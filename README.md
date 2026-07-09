# Túc Hiên Admin

## Chạy server admin

1. Mở PowerShell trong thư mục dự án.
2. Chạy:

```powershell
.venv\Scripts\python.exe .\admin_server.py
```

3. Mở trình duyệt tại:

```text
http://localhost:8001/admin
```

## Backup database

Chạy:

```powershell
.venv\Scripts\python.exe .\backup_brain_db.py
```

Database backup sẽ được lưu vào thư mục `backups/`.

## Quy trình production

- `admin_server.py` tự động tạo schema `products`, `customers`, `orders` khi khởi động.
- Dùng `run_admin_server.ps1` nếu bạn muốn chạy server bằng PowerShell.
