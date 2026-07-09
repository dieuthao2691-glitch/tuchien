import shutil
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / 'brain.db'
BACKUP_DIR = ROOT / 'backups'

BACKUP_DIR.mkdir(exist_ok=True)
now = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ')
backup_path = BACKUP_DIR / f'brain_{now}.db'

shutil.copy2(DB_PATH, backup_path)
print(f'Created backup: {backup_path}')
