"""النسخ الاحتياطي لقاعدة البيانات — database backup helpers"""
import datetime, os, shutil

from app.models import BackupConfig
from app.utils import backups_dir, config_get_int, config_set, db_file_path


def prune_backups(prefix, keep):
    """Delete all but the newest `keep` backups matching `prefix`."""
    folder = backups_dir()
    existing = sorted([f for f in os.listdir(folder) if f.startswith(prefix)], reverse=True)
    for old in existing[keep:]:
        try: os.remove(os.path.join(folder, old))
        except OSError: pass


def create_backup(prefix="wms_backup_", app=None):
    """Copy the SQLite database aside, prune old copies and record the run.

    Returns the backup filename. Raises FileNotFoundError when the database
    file cannot be located. The caller owns the transaction commit.
    """
    db_path = db_file_path(app)
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError("قاعدة البيانات غير موجودة")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{prefix}{ts}.db"
    shutil.copy2(db_path, os.path.join(backups_dir(), name))
    prune_backups(prefix, config_get_int(BackupConfig, "backup_keep_count", 10))
    config_set(BackupConfig, "last_backup", ts)
    return name


def list_backups():
    """Backup files newest-first with human readable sizes."""
    folder = backups_dir()
    files = []
    for name in sorted(os.listdir(folder), reverse=True):
        path = os.path.join(folder, name)
        if not os.path.isfile(path): continue
        size = os.path.getsize(path)
        files.append({
            "name": name, "size": size,
            "size_label": f"{size/1024/1024:.1f} MB" if size > 1024*1024 else f"{size/1024:.0f} KB",
            "created": datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
        })
    return files
