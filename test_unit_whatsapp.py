"""Unit tests — WhatsAppService"""
import io
import json
import urllib.parse
import pytest

from app.models import db, NotificationConfig
from app.services.whatsapp import WhatsAppService, _get_config


@pytest.fixture
def wa_config(app):
    """Set notification_configs rows, restoring the table afterwards."""
    def _set(**pairs):
        for k, v in pairs.items():
            row = NotificationConfig.query.filter_by(key=k).first()
            if row:
                row.value = v
            else:
                db.session.add(NotificationConfig(key=k, value=v))
        db.session.commit()

    with app.test_request_context():
        yield _set
        NotificationConfig.query.delete()
        db.session.commit()


def test_get_config_reads_rows(wa_config):
    wa_config(whatsapp_token="tok", whatsapp_phone_id="555")
    cfg = _get_config()
    assert cfg["whatsapp_token"] == "tok"
    assert cfg["whatsapp_phone_id"] == "555"


def test_send_without_cloud_api_returns_link(wa_config):
    ok, res = WhatsAppService.send("+966500000000", "مرحبا")
    assert ok is True
    assert res["method"] == "link"
    assert res["url"].startswith("https://wa.me/966500000000?text=")
    assert urllib.parse.quote("مرحبا") in res["url"]


def test_send_strips_whitespace_and_plus(wa_config):
    _, res = WhatsAppService.send("  +20111222333  ", "hi")
    assert res["url"].startswith("https://wa.me/20111222333?text=")


def test_send_falls_back_to_link_when_credentials_missing(wa_config):
    wa_config(cloud_api_enabled="true", whatsapp_token="", whatsapp_phone_id="")
    ok, res = WhatsAppService.send("+966500000000", "hi")
    assert ok is True
    assert res["method"] == "link"
    assert "fallback" not in res


def test_send_uses_cloud_api_when_configured(wa_config, monkeypatch):
    wa_config(cloud_api_enabled="true", whatsapp_token="tok", whatsapp_phone_id="555")
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.data)
        captured["timeout"] = timeout
        return io.BytesIO(json.dumps({"messages": [{"id": "wamid.1"}]}).encode())

    monkeypatch.setattr("app.services.whatsapp.urllib.request.urlopen", fake_urlopen)

    ok, res = WhatsAppService.send("+966500000000", "hello")
    assert (ok, res) == (True, {"method": "cloud_api", "msg_id": "wamid.1"})
    assert captured["url"] == f"{WhatsAppService.API_BASE}/555/messages"
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert captured["timeout"] == 15
    assert captured["body"] == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "966500000000",
        "type": "text",
        "text": {"preview_url": False, "body": "hello"},
    }


def test_send_cloud_api_missing_message_id(wa_config, monkeypatch):
    wa_config(cloud_api_enabled="true", whatsapp_token="tok", whatsapp_phone_id="555")
    monkeypatch.setattr("app.services.whatsapp.urllib.request.urlopen",
                        lambda req, timeout=None: io.BytesIO(b"{}"))
    ok, res = WhatsAppService.send("966500000000", "hello")
    assert ok is True
    assert res == {"method": "cloud_api", "msg_id": ""}


def test_send_cloud_api_error_falls_back_to_link(wa_config, monkeypatch):
    wa_config(cloud_api_enabled="true", whatsapp_token="tok", whatsapp_phone_id="555")

    def boom(req, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr("app.services.whatsapp.urllib.request.urlopen", boom)
    ok, res = WhatsAppService.send("+966500000000", "hello")
    assert ok is True
    assert res["method"] == "link"
    assert res["fallback"] is True


def test_send_notification_formats_title_and_body(wa_config, monkeypatch):
    sent = {}
    monkeypatch.setattr(WhatsAppService, "send",
                        classmethod(lambda cls, number, msg: sent.update(number=number, msg=msg) or (True, {})))

    WhatsAppService.send_notification("966500000000", "عنوان", "تفاصيل")
    assert sent["number"] == "966500000000"
    assert sent["msg"].startswith("*عنوان*\nتفاصيل")
    assert sent["msg"].endswith("— نظام النبلاء لإدارة المخازن")


def test_send_notification_without_body(wa_config, monkeypatch):
    sent = {}
    monkeypatch.setattr(WhatsAppService, "send",
                        classmethod(lambda cls, number, msg: sent.update(msg=msg) or (True, {})))

    WhatsAppService.send_notification("966500000000", "عنوان")
    assert sent["msg"].split("\n")[0] == "*عنوان*"
    assert "تفاصيل" not in sent["msg"]
