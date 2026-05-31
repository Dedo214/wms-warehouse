"""
إعدادات التطبيق لكل البيئات
Application Configuration for all environments
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """الإعدادات الأساسية المشتركة"""

    # ── App ───────────────────────────────────────────────
    APP_NAME    = "نظام إدارة المخازن"
    APP_VERSION = "2.0.0"
    SECRET_KEY  = os.environ.get("SECRET_KEY", "dev-secret-key-min-32-chars-change-in-prod")

    # ── JWT ───────────────────────────────────────────────
    JWT_SECRET_KEY              = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key-min-32-chars-prod")
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
    CORS_ORIGINS    = ["*"]
    CORS_METHODS    = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_HEADERS    = ["Content-Type", "Authorization", "X-Requested-With"]
    CORS_SUPPORTS_CREDENTIALS = True

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

