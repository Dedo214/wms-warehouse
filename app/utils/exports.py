"""ردود تنزيل الملفات — download response helpers"""
import datetime, io
from flask import send_file

CSV_MIME  = "text/csv;charset=utf-8"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME  = "application/pdf"


def export_filename(base, ext, stamp="%Y%m%d_%H%M"):
    return f"{base}_{datetime.datetime.now().strftime(stamp)}.{ext}"


def csv_download(text, filename):
    """CSV text (or StringIO) as a UTF-8 BOM download so Excel renders Arabic."""
    if hasattr(text, "getvalue"): text = text.getvalue()
    buf = io.BytesIO(text.encode("utf-8-sig"))
    buf.seek(0)
    return send_file(buf, mimetype=CSV_MIME, download_name=filename, as_attachment=True)


def xlsx_download(buf, filename):
    return send_file(buf, mimetype=XLSX_MIME, download_name=filename, as_attachment=True)


def pdf_download(buf, filename, as_attachment=True):
    return send_file(buf, mimetype=PDF_MIME, download_name=filename, as_attachment=as_attachment)


def rows_to_xlsx(headers, rows, title="Sheet1"):
    """Minimal header + rows workbook as a BytesIO buffer."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(list(headers))
    for row in rows: ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return buf


def rows_to_csv(headers, rows):
    """Header + rows as CSV text."""
    import csv
    from io import StringIO
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(list(headers))
    writer.writerows(rows)
    return out.getvalue()
