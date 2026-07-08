import json
import sqlite3
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
        if parsed.path == '/admin':
            self.serve_file('admin.html')
            return
        if parsed.path.startswith('/api/'):
            self.handle_api_get(parsed)
            return
        self.serve_file(parsed.path.lstrip('/'))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/'):
            self.handle_api_post(parsed)
            return
        send_json(self, 404, {'error': 'Not found'})

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
        data = self.read_json()
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
                cur.execute('INSERT INTO customers (name, phone, zalo, registered_at) VALUES (?, ?, ?, ?)', (
                    data.get('name'), data.get('phone', ''), data.get('zalo', ''), data.get('registered_at') or None
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
            with db_connect() as conn:
                cur = conn.cursor()
                cur.execute('UPDATE customers SET name=?, phone=?, zalo=?, registered_at=? WHERE id=?', (
                    data.get('name'), data.get('phone', ''), data.get('zalo', ''), data.get('registered_at') or None, item_id
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
        body = self.rfile.read(length) if length else b'{}'
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
