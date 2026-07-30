"""قراءة وحفظ إعدادات مفتاح/قيمة — key-value config helpers

Shared by NotificationConfig and BackupConfig which have the same shape.
"""
from app.models import db


def config_map(model):
    """All rows of a key-value config table as a plain dict."""
    return {c.key: c.value for c in model.query.all()}


def config_get(model, key, default=""):
    row = model.query.filter_by(key=key).first()
    return row.value if row and row.value is not None else default


def config_get_int(model, key, default=0):
    try: return int(config_get(model, key, default))
    except (TypeError, ValueError): return default


def config_set(model, key, value):
    row = model.query.filter_by(key=key).first()
    if row:
        row.value = str(value)
    else:
        row = model(key=key, value=str(value))
        db.session.add(row)
    return row


def config_save(model, data, keys):
    """Upsert every key present in `data`. Returns the saved keys."""
    saved = []
    for key in keys:
        if key in data:
            config_set(model, key, data[key])
            saved.append(key)
    return saved
