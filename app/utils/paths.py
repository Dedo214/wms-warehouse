"""مسارات الملفات المشتركة — shared filesystem paths"""
import os
from flask import current_app

_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_root():
    """Absolute path of the repository root (parent of the app package)."""
    try:
        root = current_app.root_path
    except RuntimeError:
        root = _PACKAGE_ROOT
    return os.path.abspath(os.path.join(root, ".."))


def uploads_dir(*sub, create=True):
    path = os.path.join(project_root(), "uploads", *sub)
    if create: os.makedirs(path, exist_ok=True)
    return path


def backups_dir(create=True):
    path = os.path.join(project_root(), "backups")
    if create: os.makedirs(path, exist_ok=True)
    return path


def db_file_path(app=None):
    """Resolve the SQLite file behind SQLALCHEMY_DATABASE_URI, or None."""
    cfg = (app or current_app).config
    uri = cfg.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite"): return None
    path = uri.replace("sqlite:///", "")
    if not os.path.isabs(path):
        path = os.path.join(project_root(), path)
    return path
