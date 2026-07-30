"""Unit tests — app.utils helpers"""
import datetime
import json
import re

from flask import g
from flask_jwt_extended import create_access_token

from app.models import db, User, Item
from app.utils import (ok, created, err, not_found, forbidden, unauthorized,
                       server_err, paginate, gen_ref, parse_date, today_str,
                       require_role, validate)


def _body(resp):
    payload, code = resp
    return json.loads(payload.get_data()), code


def test_ok_defaults(app):
    with app.test_request_context():
        body, code = _body(ok())
        assert code == 200
        assert body == {"success": True, "message": "", "data": None}


def test_ok_with_payload(app):
    with app.test_request_context():
        body, code = _body(ok({"x": 1}, "تم", 202))
        assert code == 202
        assert body == {"success": True, "message": "تم", "data": {"x": 1}}


def test_created_returns_201(app):
    with app.test_request_context():
        body, code = _body(created({"id": 5}))
        assert code == 201
        assert body["data"] == {"id": 5}
        assert body["message"] == "تم الإنشاء بنجاح"


def test_err_without_errors_dict(app):
    with app.test_request_context():
        body, code = _body(err("فشل"))
        assert code == 400
        assert body == {"success": False, "error": "فشل"}


def test_err_with_field_errors(app):
    with app.test_request_context():
        body, code = _body(err("فشل", 422, {"name": "مطلوب"}))
        assert code == 422
        assert body["errors"] == {"name": "مطلوب"}


def test_error_shortcuts(app):
    with app.test_request_context():
        assert _body(not_found())[1] == 404
        assert _body(forbidden())[1] == 403
        assert _body(unauthorized())[1] == 401
        assert _body(server_err())[1] == 500
        assert _body(not_found("مخصص"))[0]["error"] == "مخصص"


def test_paginate_first_page(app):
    with app.app_context():
        res = paginate(Item.query.order_by(Item.id), page=1, per_page=5)
        assert len(res["items"]) == 5
        assert res["page"] == 1
        assert res["per_page"] == 5
        assert res["pages"] == -(-res["total"] // 5)
        assert res["has_next"] is True
        assert res["has_prev"] is False


def test_paginate_second_page_is_disjoint(app):
    with app.app_context():
        p1 = paginate(Item.query.order_by(Item.id), page=1, per_page=3)
        p2 = paginate(Item.query.order_by(Item.id), page=2, per_page=3)
        assert {i.id for i in p1["items"]}.isdisjoint({i.id for i in p2["items"]})
        assert p2["has_prev"] is True


def test_paginate_caps_per_page(app):
    with app.app_context():
        res = paginate(Item.query, page=1, per_page=500, max_per=10)
        assert res["per_page"] == 10
        assert len(res["items"]) <= 10


def test_paginate_empty_query_has_one_page(app):
    with app.app_context():
        res = paginate(Item.query.filter(Item.code == "__missing__"))
        assert res["total"] == 0
        assert res["items"] == []
        assert res["pages"] == 1
        assert res["has_next"] is False


def test_gen_ref_format_and_uniqueness():
    ref = gen_ref("PR")
    assert re.fullmatch(r"PR-\d{6}-[0-9A-F]{4}", ref)
    assert ref.split("-")[1] == datetime.datetime.utcnow().strftime("%y%m%d")
    assert len({gen_ref("PR") for _ in range(50)}) > 1


def test_parse_date_valid():
    assert parse_date("2024-05-17") == datetime.datetime(2024, 5, 17)


def test_parse_date_invalid_or_empty():
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("17/05/2024") is None
    assert parse_date("not-a-date") is None


def test_today_str():
    assert today_str() == datetime.datetime.utcnow().strftime("%Y-%m-%d")


def test_validate_collects_missing_and_blank_fields():
    errs = validate({"a": "v", "b": "", "c": None}, ["a", "b", "c", "d"])
    assert set(errs) == {"b", "c", "d"}
    assert "b" in errs["b"]


def test_validate_accepts_falsy_but_present_values():
    assert validate({"qty": 0, "flag": False}, ["qty", "flag"]) == {}


def _guarded(*roles):
    @require_role(*roles)
    def view():
        return g.current_user.username
    return view


def _call(app, view, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with app.test_request_context("/guarded", headers=headers):
        return view()


def test_require_role_rejects_missing_token(app):
    result = _call(app, _guarded("admin"))
    body, code = _body(result)
    assert code == 401
    assert body["success"] is False


def test_require_role_rejects_malformed_token(app):
    body, code = _body(_call(app, _guarded("admin"), token="not.a.jwt"))
    assert code == 401
    assert body["success"] is False


def test_require_role_allows_matching_role(app):
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        token = create_access_token(identity=str(admin.id))
    assert _call(app, _guarded("admin"), token) == "admin"


def test_require_role_blocks_other_roles(app):
    with app.app_context():
        viewer = User.query.filter_by(username="viewer").first()
        token = create_access_token(identity=str(viewer.id))
    body, code = _body(_call(app, _guarded("admin", "manager"), token))
    assert code == 403
    assert "admin" in body["error"]


def test_require_role_without_roles_allows_any_active_user(app):
    with app.app_context():
        viewer = User.query.filter_by(username="viewer").first()
        token = create_access_token(identity=str(viewer.id))
    assert _call(app, _guarded(), token) == "viewer"


def test_require_role_blocks_inactive_user(app):
    with app.app_context():
        user = User(name="معطل", username="unit_inactive", role="admin", is_active=False)
        user.set_password("secret123")
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        uid = user.id
    try:
        body, code = _body(_call(app, _guarded("admin"), token))
        assert code == 403
        assert body["success"] is False
    finally:
        with app.app_context():
            db.session.delete(db.session.get(User, uid))
            db.session.commit()
