import json
import sqlite3
import os
import hmac
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / 'brain.db'


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class AdminHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.serve_file('index.html')
            return
        if parsed.path in ('/admin', '/admin/'):
            self.serve_file('admin.html')
            return
        if parsed.path in ('/payment', '/payment/'):
            self.serve_file('payment.html')
            return
        if parsed.path.startswith('/api/'):
            self.handle_api_get(parsed)
            return
        self.serve_file(parsed.path.lstrip('/'))

    def do_POST(self):
        parsed = urlparse(self.path)
        print(f'POST request path: {parsed.path}')
        if parsed.path in ('/api/sepay/webhook', '/api/sepay/webhook/'):
            self.handle_sepay_webhook()
            return
        if parsed.path.startswith('/api/'):
            try:
                self.handle_api_post(parsed)
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_json(self, 500, {'error': 'Internal server error', 'detail': str(e)})
            return
        print('POST not found for path:', parsed.path)
        send_json(self, 404, {'error': 'Not found'})

    def handle_sepay_webhook(self):
        # Generic webhook receiver for SePay -> map to create_order
        # Read raw body so we can verify signature
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length) if length else b'{}'

        # Verify signature if secret provided
        def get_secret():
            # Prefer environment variable, fallback to sepay_secret.txt in project root
            s = os.environ.get('SEPAY_WEBHOOK_SECRET')
            if s:
                return s
            secret_file = ROOT / 'sepay_secret.txt'
            if secret_file.exists():
                return secret_file.read_text(encoding='utf-8').strip()
            return None

        secret = get_secret()
        sig_hdr = self.headers.get('X-Sepay-Signature') or self.headers.get('X-Signature')
        if secret:
            if not sig_hdr:
                send_json(self, 401, {'error': 'Missing signature header'})
                return
            # Accept formats like 'sha256=abcd...' or raw hex
            provided = sig_hdr.split('=')[-1]
            computed = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(provided, computed):
                send_json(self, 401, {'error': 'Invalid signature'})
                return

        try:
            data = json.loads(body.decode('utf-8')) if body else {}
        except Exception as e:
            send_json(self, 400, {'error': 'Invalid JSON', 'detail': str(e)})
            return
        # normalize status naming: map 'paid' -> 'success'
        if data.get('status') == 'paid':
            data['status'] = 'success'
        # Try to extract phone or create customer
        phone = data.get('customer_phone') or data.get('phone') or data.get('payer_phone')
        customer_id = None
        if phone:
            with db_connect() as conn:
                row = conn.execute('SELECT id FROM customers WHERE phone=?', (phone,)).fetchone()
                if row:
                    customer_id = row['id']
                else:
                    cur = conn.cursor()
                    from datetime import datetime
                    registered_at = datetime.utcnow().isoformat() + 'Z'
                    cur.execute('INSERT INTO customers (name, phone, zalo, registered_at) VALUES (?, ?, ?, ?)', (phone, phone, '', registered_at))
                    conn.commit()
                    customer_id = cur.lastrowid

        # Normalize data for create_order
        normalized = {
            'customer_id': int(customer_id) if customer_id is not None else None,
            'product_id': int(data['product_id']) if data.get('product_id') else None,
            'amount': float(data.get('amount') or data.get('value') or 0),
            'status': data.get('status') or ('paid' if data.get('paid') else 'pending'),
            'order_date': data.get('timestamp') or data.get('order_date') or None
        }
        if normalized['order_date'] is None:
            from datetime import datetime
            normalized['order_date'] = datetime.utcnow().isoformat() + 'Z'

        # If product_id missing, try to infer from metadata
        meta_pid = None
        if not normalized['product_id'] and isinstance(data.get('metadata'), dict):
            meta_pid = data['metadata'].get('product_id')
        if meta_pid:
            try:
                normalized['product_id'] = int(meta_pid)
            except Exception:
                pass

        # Try to find an existing order by scanning common note/remark fields for order id
        order_ref = None
        for key in ('note', 'message', 'description', 'remark', 'transfer_note'):
            val = data.get(key)
            if isinstance(val, str):
                import re
                m = re.search(r'(?:Đơn#|ORDER#|order_id=)(\d+)', val, re.IGNORECASE)
                if m:
                    order_ref = int(m.group(1))
                    break

        if order_ref:
            # Update the existing order status instead of creating a new one
            try:
                with db_connect() as conn:
                    cur = conn.cursor()
                    cur.execute('UPDATE orders SET status=? WHERE id=?', (normalized.get('status') or 'success', order_ref))
                    conn.commit()
                send_json(self, 200, {'message': 'Order updated', 'order_id': order_ref})
                return
            except Exception as e:
                send_json(self, 500, {'error': 'Failed to update order', 'detail': str(e)})
                return

        # Call existing create_order which handles stock decrement for physical products
        try:
            # create_order will send its own JSON response
            self.create_order(normalized)
        except Exception as e:
            send_json(self, 500, {'error': 'Webhook handling failed', 'detail': str(e)})

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/'):
            self.handle_api_put(parsed)
            return
        send_json(self, 404, {'error': 'Not found'})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/'):
            self.handle_api_delete(parsed)
            return
        send_json(self, 404, {'error': 'Not found'})

    def serve_file(self, relative_path):
        path = (ROOT / relative_path).resolve()
        if not str(path).startswith(str(ROOT)):
            send_json(self, 403, {'error': 'Forbidden'})
            return
        if not path.exists():
            send_json(self, 404, {'error': 'Not found'})
            return
        # Serve admin.html dynamically with server-rendered tables + initial state
        if path.name == 'admin.html':
            html = path.read_text(encoding='utf-8')
            # load fresh data
            with db_connect() as conn:
                products = [dict(r) for r in conn.execute('SELECT * FROM products ORDER BY id').fetchall()]
                customers = [dict(r) for r in conn.execute('SELECT * FROM customers ORDER BY id').fetchall()]
                orders = [dict(r) for r in conn.execute('SELECT * FROM orders ORDER BY id').fetchall()]

            def render_products_table(items):
                if not items:
                    return '<div class="empty">Chưa có sản phẩm.</div>'
                rows = []
                for it in items:
                    rows.append(f"<tr><td>{it['id']}</td><td><strong>{it['name']}</strong><br><span style=\"color:#75695f;font-size:13px\">{(it.get('description') or '')}</span></td><td>{it.get('product_type','')}</td><td>{int(it.get('price') or 0):,}₫</td><td>{it.get('stock_quantity') or 0}</td><td><div class=\"actions\"><button class=\"btn btn-secondary\">Sửa</button><button class=\"btn btn-danger\">Xóa</button></div></td></tr>")
                return '<table><thead><tr><th>ID</th><th>Tên</th><th>Loại</th><th>Giá</th><th>Tồn kho</th><th></th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'

            def render_customers_table(items):
                if not items:
                    return '<div class="empty">Chưa có khách hàng.</div>'
                rows = []
                for it in items:
                    rows.append(f"<tr><td>{it['id']}</td><td><strong>{it.get('name') or ''}</strong></td><td>{it.get('phone') or ''}</td><td>{it.get('zalo') or ''}</td><td>{it.get('registered_at') or ''}</td><td><div class=\"actions\"><button class=\"btn btn-secondary\">Sửa</button><button class=\"btn btn-danger\">Xóa</button></div></td></tr>")
                return '<table><thead><tr><th>ID</th><th>Tên</th><th>Điện thoại</th><th>Zalo</th><th>Ngày đăng ký</th><th></th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'

            def render_orders_table(items):
                if not items:
                    return '<div class="empty">Chưa có đơn hàng.</div>'
                rows = []
                for it in items:
                    rows.append(f"<tr><td>{it['id']}</td><td>{it.get('customer_id') or ''}</td><td>{it.get('product_id') or ''}</td><td>{int(it.get('amount') or 0):,}₫</td><td>{it.get('status') or ''}</td><td>{it.get('order_date') or ''}</td><td><div class=\"actions\"><button class=\"btn btn-secondary\">Sửa</button><button class=\"btn btn-danger\">Xóa</button></div></td></tr>")
                return '<table><thead><tr><th>ID</th><th>Khách hàng</th><th>Sản phẩm</th><th>Số tiền</th><th>Trạng thái</th><th>Ngày</th><th></th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'

            html = html.replace('<div id="productsTable"></div>', render_products_table(products))
            html = html.replace('<div id="customersTable"></div>', render_customers_table(customers))
            html = html.replace('<div id="ordersTable"></div>', render_orders_table(orders))
            # inject initial state for client JS
            initial = json.dumps({'products': products, 'customers': customers, 'orders': orders}, ensure_ascii=False)
            inject = f"<script>window.__INITIAL_STATE__ = {initial};</script>"
            html = html.replace('</body>', inject + '\n</body>')

            data = html.encode('utf-8')
            content_type = 'text/html; charset=utf-8'
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(data)
            return

        data = path.read_bytes()
        content_type = 'text/html; charset=utf-8' if path.suffix.lower() in {'.html', '.htm'} else 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(data)

    def handle_api_get(self, parsed):
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) < 2:
            send_json(self, 400, {'error': 'Bad request'})
            return
        resource = parts[1]
        if resource == 'products':
            rows = self.fetch_products()
            send_json(self, 200, rows)
        elif resource == 'customers':
            rows = self.fetch_customers()
            send_json(self, 200, rows)
        elif resource == 'orders':
            rows = self.fetch_orders()
            send_json(self, 200, rows)
        else:
            send_json(self, 404, {'error': 'Not found'})

    def handle_api_post(self, parsed):
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) < 2:
            send_json(self, 400, {'error': 'Bad request'})
            return
        resource = parts[1]
        print('API post headers:', dict(self.headers))
        data = self.read_json()
        print('Parsed JSON body:', data)
        # special create_checkout endpoint for landing payment flow
        if resource == 'create_checkout':
            # expected: name, phone, email, service_name, price, product_id(optional)
            name = data.get('name') or ''
            phone = (data.get('phone') or '').strip()
            email = (data.get('email') or '').strip()
            service_name = data.get('service_name') or data.get('service') or 'Order'
            price = float(data.get('price') or 0)
            product_id = data.get('product_id')

            # basic validation
            if not phone:
                send_json(self, 400, {'error': 'Phone is required'})
                return

            with db_connect() as conn:
                cur = conn.cursor()
                row = cur.execute('SELECT id FROM customers WHERE phone=?', (phone,)).fetchone()
                if row:
                    customer_id = row['id']
                else:
                    from datetime import datetime
                    registered_at = datetime.utcnow().isoformat() + 'Z'
                    cur.execute('INSERT INTO customers (name, phone, zalo, registered_at) VALUES (?, ?, ?, ?)', (name or phone, phone, '', registered_at))
                    conn.commit()
                    customer_id = cur.lastrowid

                # create pending order
                from datetime import datetime
                order_date = datetime.utcnow().isoformat() + 'Z'
                print('Creating checkout order:', {'customer_id': customer_id, 'product_id': product_id, 'price': price, 'order_date': order_date})
                cur.execute('INSERT INTO orders (customer_id, product_id, amount, status, order_date) VALUES (?, ?, ?, ?, ?)', (
                    customer_id, int(product_id) if product_id else None, price, 'pending', order_date
                ))
                conn.commit()
                order_id = cur.lastrowid

            payment_url = f"/payment?order_id={order_id}"
            send_json(self, 201, {'order_id': order_id, 'payment_url': payment_url})
            return
        if resource == 'products':
            with db_connect() as conn:
                cur = conn.cursor()
                cur.execute('INSERT INTO products (name, product_type, price, description, stock_quantity) VALUES (?, ?, ?, ?, ?)', (
                    data.get('name'), data.get('product_type', 'service'), data.get('price', 0), data.get('description', ''), data.get('stock_quantity', 0)
                ))
                conn.commit()
            send_json(self, 201, {'message': 'Product created'})
        elif resource == 'customers':
            with db_connect() as conn:
                cur = conn.cursor()
                from datetime import datetime
                registered_at = data.get('registered_at') or datetime.utcnow().isoformat() + 'Z'
                cur.execute('INSERT INTO customers (name, phone, zalo, registered_at) VALUES (?, ?, ?, ?)', (
                    data.get('name'), data.get('phone', ''), data.get('zalo', ''), registered_at
                ))
                conn.commit()
            send_json(self, 201, {'message': 'Customer created'})
        elif resource == 'orders':
            self.create_order(data)
        else:
            send_json(self, 404, {'error': 'Not found'})

    def handle_api_put(self, parsed):
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) < 3:
            send_json(self, 400, {'error': 'Bad request'})
            return
        resource = parts[1]
        item_id = int(parts[2])
        data = self.read_json()
        if resource == 'products':
            with db_connect() as conn:
                cur = conn.cursor()
                cur.execute('UPDATE products SET name=?, product_type=?, price=?, description=?, stock_quantity=? WHERE id=?', (
                    data.get('name'), data.get('product_type', 'service'), data.get('price', 0), data.get('description', ''), data.get('stock_quantity', 0), item_id
                ))
                conn.commit()
            send_json(self, 200, {'message': 'Product updated'})
        elif resource == 'customers':
            from datetime import datetime
            with db_connect() as conn:
                cur = conn.cursor()
                registered_at = data.get('registered_at') or datetime.utcnow().isoformat() + 'Z'
                cur.execute('UPDATE customers SET name=?, phone=?, zalo=?, registered_at=? WHERE id=?', (
                    data.get('name'), data.get('phone', ''), data.get('zalo', ''), registered_at, item_id
                ))
                conn.commit()
            send_json(self, 200, {'message': 'Customer updated'})
        elif resource == 'orders':
            self.update_order(item_id, data)
        else:
            send_json(self, 404, {'error': 'Not found'})

    def handle_api_delete(self, parsed):
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) < 3:
            send_json(self, 400, {'error': 'Bad request'})
            return
        resource = parts[1]
        item_id = int(parts[2])
        if resource == 'products':
            with db_connect() as conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM products WHERE id=?', (item_id,))
                conn.commit()
            send_json(self, 200, {'message': 'Product deleted'})
        elif resource == 'customers':
            with db_connect() as conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM customers WHERE id=?', (item_id,))
                conn.commit()
            send_json(self, 200, {'message': 'Customer deleted'})
        elif resource == 'orders':
            with db_connect() as conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM orders WHERE id=?', (item_id,))
                conn.commit()
            send_json(self, 200, {'message': 'Order deleted'})
        else:
            send_json(self, 404, {'error': 'Not found'})

    def read_json(self):
        length = int(self.headers.get('Content-Length', '0'))
        print('read_json length:', length)
        body = self.rfile.read(length) if length else b'{}'
        print('read_json raw body:', body)
        return json.loads(body.decode('utf-8')) if body else {}

    def fetch_products(self):
        with db_connect() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY id').fetchall()
            return [dict(r) for r in rows]

    def fetch_customers(self):
        with db_connect() as conn:
            rows = conn.execute('SELECT * FROM customers ORDER BY id').fetchall()
            return [dict(r) for r in rows]

    def fetch_orders(self):
        with db_connect() as conn:
            rows = conn.execute('SELECT * FROM orders ORDER BY id').fetchall()
            return [dict(r) for r in rows]

    def create_order(self, data):
        customer_id = int(data.get('customer_id'))
        product_id = int(data.get('product_id'))
        amount = float(data.get('amount', 0))
        status = data.get('status', 'pending')
        order_date = data.get('order_date') or None
        if order_date is None:
            from datetime import datetime
            order_date = datetime.utcnow().isoformat() + 'Z'
        with db_connect() as conn:
            cur = conn.cursor()
            product = cur.execute('SELECT product_type, stock_quantity FROM products WHERE id=?', (product_id,)).fetchone()
            if not product:
                send_json(self, 400, {'error': 'Product not found'})
                return
            if product['product_type'] == 'physical':
                if product['stock_quantity'] is None:
                    product['stock_quantity'] = 0
                if int(product['stock_quantity']) <= 0:
                    send_json(self, 400, {'error': 'Out of stock'})
                    return
                cur.execute('UPDATE products SET stock_quantity = stock_quantity - 1 WHERE id=?', (product_id,))
            cur.execute('INSERT INTO orders (customer_id, product_id, amount, status, order_date) VALUES (?, ?, ?, ?, ?)', (
                customer_id, product_id, amount, status, order_date
            ))
            conn.commit()
        send_json(self, 201, {'message': 'Order created'})

    def update_order(self, order_id, data):
        customer_id = int(data.get('customer_id'))
        product_id = int(data.get('product_id'))
        amount = float(data.get('amount', 0))
        status = data.get('status', 'pending')
        order_date = data.get('order_date') or None
        with db_connect() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE orders SET customer_id=?, product_id=?, amount=?, status=?, order_date=? WHERE id=?', (
                customer_id, product_id, amount, status, order_date, order_id
            ))
            conn.commit()
        send_json(self, 200, {'message': 'Order updated'})


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', 8001), AdminHandler)
    print('Admin server running on http://localhost:8001/admin')
    server.serve_forever()
