"""إرسال البريد عبر إعدادات SMTP المحفوظة — SMTP mail sending"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.models import NotificationConfig, User
from app.utils import config_map


def smtp_settings():
    """SMTP settings stored in NotificationConfig."""
    cfg = config_map(NotificationConfig)
    return {
        "host":    cfg.get("smtp_host",""),
        "port":    int(cfg.get("smtp_port") or 587),
        "user":    cfg.get("smtp_user",""),
        "password":cfg.get("smtp_pass",""),
        "sender":  cfg.get("email_from","") or cfg.get("smtp_user","") or "noreply@wms.local",
        # absent key means "not configured yet" and does not block sending
        "enabled": cfg.get("email_enabled","true") == "true",
    }


def admin_emails():
    return [u.email for u in
            User.query.filter(User.role.in_(["admin","super_admin"])).all() if u.email]


def send_email(subject, body, recipients, settings=None):
    """Send one message per recipient. Returns the number of messages sent."""
    cfg = settings or smtp_settings()
    if not cfg["host"]: return 0
    sent = 0
    for to in recipients:
        msg = MIMEMultipart()
        msg["From"] = cfg["sender"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as s:
            s.starttls()
            if cfg["user"] and cfg["password"]:
                s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
        sent += 1
    return sent


def send_notification_email(subject, body, to=None):
    """Best-effort notification mail to `to` (or every admin); never raises."""
    try:
        cfg = smtp_settings()
        if not cfg["host"] or not cfg["enabled"]: return 0
        recipients = [to] if to else admin_emails()
        sent = 0
        for r in recipients:
            try: sent += send_email(subject, body, [r], cfg)
            except Exception: pass
        return sent
    except Exception:
        return 0
