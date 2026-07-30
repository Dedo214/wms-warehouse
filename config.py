"""
إعدادات التطبيق لكل البيئات
Application Configuration for all environments
"""
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_secret(name: str) -> str:
    """Return a secret from the environment.

    In production the secret MUST be supplied via the environment; otherwise a
    fresh random value is generated per process so development never relies on a
    known, hardcoded key that could be used to forge sessions/JWTs.
    """
    val = os.environ.get(name)
    if val:
        return val
    if os.environ.get("FLASK_ENV", "development").lower() == "production":
        raise RuntimeError(
            f"{name} must be set via the environment in production."
        )
    return secrets.token_urlsafe(48)


class Config:
    """الإعدادات الأساسية المشتركة"""

    # ── App ───────────────────────────────────────────────
    APP_NAME    = "نظام إدارة المخازن"
    APP_VERSION = "2.0.0"
    SECRET_KEY  = _get_secret("SECRET_KEY")

    # ── JWT ───────────────────────────────────────────────
    JWT_SECRET_KEY              = _get_secret("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES    = timedelta(hours=12)
    JWT_REFRESH_TOKEN_EXPIRES   = timedelta(days=30)
    JWT_ALGORITHM               = "HS256"
    JWT_TOKEN_LOCATION          = ["headers"]
    JWT_HEADER_NAME             = "Authorization"
    JWT_HEADER_TYPE             = "Bearer"

    # ── Database ──────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI         = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'warehouse.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS  = False
    SQLALCHEMY_ENGINE_OPTIONS       = {
        "pool_pre_ping": True,
        "pool_recycle":  300,
    }

    # ── CORS ──────────────────────────────────────────────
    # Comma-separated allowlist via CORS_ORIGINS (e.g. "https://app.example.com").
    # Defaults to "*" for convenience, but credentials are NEVER combined with a
    # wildcard origin (that combination is invalid/unsafe). Auth uses the
    # Authorization header (JWT), so credentialed CORS is not required.
    CORS_ORIGINS    = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
    CORS_METHODS    = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_HEADERS    = ["Content-Type", "Authorization", "X-Requested-With"]
    CORS_SUPPORTS_CREDENTIALS = False

    # ── Pagination ────────────────────────────────────────
    DEFAULT_PAGE_SIZE = 30
    MAX_PAGE_SIZE     = 200

    # ── Upload ────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER      = os.path.join(BASE_DIR, "uploads")

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL = "INFO"
    LOG_FILE  = os.path.join(BASE_DIR, "logs", "app.log")

    DEBUG   = False
    TESTING = False


class DevelopmentConfig(Config):
    """بيئة التطوير"""
    DEBUG     = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///C:\\web-projects\\wms_dev.db"
    )


class ProductionConfig(Config):
    """بيئة الإنتاج"""
    DEBUG     = False
    LOG_LEVEL = "WARNING"
    # In production always set DATABASE_URL in environment


class TestingConfig(Config):
    """بيئة الاختبار"""
    TESTING                 = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    RATELIMIT_ENABLED        = False


# ── Config registry ──────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
    "default":     DevelopmentConfig,
}


def get_config() -> Config:
    env = os.environ.get("FLASK_ENV", "development").lower()
    return config_map.get(env, DevelopmentConfig)

