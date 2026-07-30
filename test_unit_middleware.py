"""Unit tests — app.middleware (JWT callbacks, request hooks, error handlers)"""
import json
import datetime

from flask_jwt_extended import create_access_token
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnprocessableEntity

from app.models import User


def _json(resp):
    return json.loads(resp.data)


def _handler(app, code):
    """The single error handler registered for an HTTP status code."""
    handlers = app.error_handler_spec[None][code]
    assert len(handlers) == 1
    return next(iter(handlers.values()))


# ── Request hooks ────────────────────────────────────────────
def test_security_headers_added_to_every_response(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_response_time_header_is_reported_in_ms(client):
    resp = client.get("/health")
    value = resp.headers["X-Response-Time"]
    assert value.endswith("ms")
    assert float(value[:-2]) >= 0


# ── Error handlers ───────────────────────────────────────────
def test_unknown_path_returns_json_404(client):
    resp = client.get("/api/definitely-not-a-route")
    assert resp.status_code == 404
    body = _json(resp)
    assert body["success"] is False
    assert body["error"] == "المسار غير موجود"


def test_wrong_method_returns_json_405(client, auth):
    resp = client.delete("/api/auth/login", headers=auth)
    assert resp.status_code == 405
    assert _json(resp)["error"] == "الطريقة غير مسموحة"


def test_error_handlers_registered_for_all_documented_codes(app):
    handled = set(app.error_handler_spec[None].keys())
    assert {400, 404, 405, 413, 422, 500} <= handled


def test_error_handler_bodies(app):
    with app.test_request_context():
        for exc, code, message in [
            (BadRequest(), 400, "طلب غير صالح"),
            (RequestEntityTooLarge(), 413, "الملف كبير جداً"),
            (UnprocessableEntity(), 422, "بيانات غير قابلة للمعالجة"),
            (RuntimeError("boom"), 500, "خطأ داخلي في الخادم"),
        ]:
            payload, status = _handler(app, code)(exc)
            body = json.loads(payload.get_data())
            assert status == code
            assert body["success"] is False
            assert body["error"] == message


def test_bad_request_handler_includes_detail(app):
    with app.test_request_context():
        payload, _ = _handler(app, 400)(BadRequest("مفصّل"))
        assert "detail" in json.loads(payload.get_data())


# ── JWT callbacks ────────────────────────────────────────────
def test_missing_token_message(client):
    resp = client.get("/api/items")
    assert resp.status_code == 401
    assert _json(resp)["error"] == "مطلوب تسجيل الدخول أولاً"


def test_invalid_token_message(client):
    resp = client.get("/api/items", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401
    body = _json(resp)
    assert body["success"] is False
    assert body["error"].startswith("توكن غير صالح")


def test_expired_token_message(client, app):
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        token = create_access_token(identity=str(admin.id),
                                    expires_delta=datetime.timedelta(seconds=-1))
    resp = client.get("/api/items", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert _json(resp)["error"] == "انتهت صلاحية الجلسة، سجّل الدخول مجدداً"
