"""أدوات مساعدة مشتركة"""
import os, json, datetime
from functools import wraps
from flask import jsonify, request, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.utils.barcodes import barcode_png, barcode_png_file
from app.utils.configs import (config_map, config_get, config_get_int,
                               config_set, config_save)
from app.utils.exports import (csv_download, export_filename, pdf_download,
                               rows_to_csv, rows_to_xlsx, xlsx_download)
from app.utils.files import (ALLOWED_EXTENSIONS, IMAGE_EXTENSIONS,
                             MAX_FILE_SIZE, MAX_IMAGE_SIZE, file_ext,
                             file_size, unique_filename, validate_upload)
from app.utils.paths import backups_dir, db_file_path, project_root, uploads_dir

# ── Response helpers ─────────────────────────────────────────
def ok(data=None, message="", code=200):
    return jsonify({"success":True,"message":message,"data":data}), code

def created(data=None, message="تم الإنشاء بنجاح"):
    return ok(data, message, 201)

def err(message, code=400, errors=None):
    body = {"success":False,"error":message}
    if errors: body["errors"] = errors
    return jsonify(body), code

def not_found(msg="غير موجود"):      return err(msg, 404)
def forbidden(msg="غير مصرح"):       return err(msg, 403)
def unauthorized(msg="غير مخوّل"):   return err(msg, 401)
def server_err(msg="خطأ في الخادم"): return err(msg, 500)

# ── Pagination ───────────────────────────────────────────────
def paginate(query, page=1, per_page=30, max_per=200):
    per_page = min(per_page, max_per)
    total    = query.count()
    items    = query.offset((page-1)*per_page).limit(per_page).all()
    return {"items":items,"total":total,"page":page,"per_page":per_page,
            "pages":max(1,(total+per_page-1)//per_page),
            "has_next":page*per_page<total,"has_prev":page>1}

# ── Ref number ───────────────────────────────────────────────
def gen_ref(prefix):
    ts   = datetime.datetime.utcnow().strftime("%y%m%d")
    rand = os.urandom(2).hex().upper()
    return f"{prefix}-{ts}-{rand}"

# ── Date parser ──────────────────────────────────────────────
def parse_date(s):
    if not s: return None
    try: return datetime.datetime.strptime(s, "%Y-%m-%d")
    except: return None

def today_str():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

# ── Role decorator ───────────────────────────────────────────
def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from app.models import User
            try: verify_jwt_in_request()
            except Exception: return unauthorized("توكن غير صالح أو منتهٍ")
            user = User.query.get(current_uid())
            if not user or not user.is_active:
                return forbidden("الحساب غير مفعّل")
            if roles and user.role not in roles:
                return forbidden(f"يتطلب أحد الأدوار: {', '.join(roles)}")
            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ── Current user ─────────────────────────────────────────────
def current_uid():
    return int(get_jwt_identity())

def current_user():
    """The User behind the request JWT (None when it no longer exists)."""
    from app.models import User
    user = getattr(g, "current_user", None)
    if user is not None: return user
    return User.query.get(current_uid())

# ── Partial update ───────────────────────────────────────────
def apply_fields(obj, data, fields, cast=None):
    """Copy the given keys from `data` onto `obj` when present."""
    for f in fields:
        if f in data: setattr(obj, f, cast(data[f]) if cast else data[f])
    return obj

# ── Query-string filters ─────────────────────────────────────
def args_filters(*keys):
    """Non-empty request.args values for `keys`, as a filters dict."""
    filters = {}
    for k in keys:
        v = request.args.get(k)
        if v: filters[k] = v
    return filters

# ── Validate required fields ─────────────────────────────────
def validate(data, fields):
    errs = {}
    for f in fields:
        if data.get(f) is None or data.get(f) == "":
            errs[f] = f"الحقل '{f}' مطلوب"
    return errs
