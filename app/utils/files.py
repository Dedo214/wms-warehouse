"""التعامل مع الملفات المرفوعة — upload validation helpers"""
import datetime, os
from werkzeug.utils import secure_filename

MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {"pdf","jpg","jpeg","png","gif","doc","docx","xls","xlsx","csv","txt","zip"}
IMAGE_EXTENSIONS = {"jpg","jpeg","png","gif","webp"}


def file_ext(f):
    name = getattr(f, "filename", "") or ""
    return name.rsplit(".",1)[-1].lower() if "." in name else ""


def file_size(f):
    """Size of an uploaded stream, leaving it rewound."""
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    return size


def validate_upload(f, allowed=ALLOWED_EXTENSIONS, max_size=MAX_FILE_SIZE, type_message=None):
    """Return an Arabic error message, or None when the upload is acceptable."""
    if not f or not getattr(f, "filename", ""):
        return "الملف مطلوب"
    if file_ext(f) not in allowed:
        return type_message or f"نوع الملف غير مسموح: {', '.join(sorted(allowed))} فقط"
    if file_size(f) > max_size:
        return f"حجم الملف يتجاوز {max_size // (1024*1024)} ميجابايت"
    return None


def unique_filename(prefix, original="", ext=None):
    """`prefix` + timestamp + sanitised original name, safe to store on disk."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if ext: return f"{prefix}_{ts}.{ext}"
    return f"{prefix}_{ts}_{secure_filename(original)}"
