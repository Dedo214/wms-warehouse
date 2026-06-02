import json, urllib.request, urllib.parse, urllib.error
from flask import current_app

class WhatsAppService:
    API_BASE = "https://graph.facebook.com/v18.0"

    @classmethod
    def send(cls, to_number: str, message: str) -> tuple:
        cfg = _get_config()
        if not cfg.get("cloud_api_enabled"):
            url = f"https://wa.me/{to_number.strip().lstrip('+')}?text={urllib.parse.quote(message)}"
            return True, {"method":"link","url":url}
        token = cfg.get("whatsapp_token","")
        phone_id = cfg.get("whatsapp_phone_id","")
        if not token or not phone_id:
            url = f"https://wa.me/{to_number.strip().lstrip('+')}?text={urllib.parse.quote(message)}"
            return True, {"method":"link","url":url}
        try:
            data = json.dumps({
                "messaging_product":"whatsapp",
                "recipient_type":"individual",
                "to": to_number.replace("+","").strip(),
                "type":"text",
                "text":{"preview_url":False,"body":message}
            }).encode()
            req = urllib.request.Request(
                f"{cls.API_BASE}/{phone_id}/messages",
                data=data,
                headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read())
            return True, {"method":"cloud_api","msg_id":result.get("messages",[{}])[0].get("id","")}
        except Exception as e:
            current_app.logger.error(f"WhatsApp API error: {e}")
            url = f"https://wa.me/{to_number.strip().lstrip('+')}?text={urllib.parse.quote(message)}"
            return True, {"method":"link","url":url,"fallback":True}

    @classmethod
    def send_notification(cls, number: str, title: str, body: str = "") -> tuple:
        msg = f"*{title}*\n{body}" if body else f"*{title}*"
        msg += "\n\n— نظام النبلاء لإدارة المخازن"
        return cls.send(number, msg)

def _get_config():
    from app.models import NotificationConfig
    configs = NotificationConfig.query.all()
    d = {c.key: c.value for c in configs}
    return d
