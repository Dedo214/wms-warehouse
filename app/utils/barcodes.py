"""توليد صور الباركود — Code128 barcode rendering"""
import io


def _code128(code):
    import barcode as bc_lib
    from barcode.writer import ImageWriter
    return bc_lib.get_barcode_class("code128")(code, writer=ImageWriter())


def barcode_png(code):
    """PNG bytes of a Code128 barcode, or None when python-barcode is missing."""
    try:
        buf = io.BytesIO()
        _code128(code).write(buf)
        buf.seek(0)
        return buf
    except ImportError:
        return None


def barcode_png_file(code, path):
    """Write a Code128 barcode to `path`; returns the path, or None if unavailable."""
    try:
        with open(path, "wb") as fh:
            _code128(code).write(fh)
        return path
    except ImportError:
        return None
