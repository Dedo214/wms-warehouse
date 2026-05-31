"""pytest fixtures"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
config.DevelopmentConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

from app import create_app

@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config["TESTING"] = True
    yield app

@pytest.fixture(scope="session")
def client(app):
    return app.test_client()

@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/api/auth/login",
                    json={"username":"admin","password":"admin123"})
    import json
    return json.loads(r.data)["data"]["access_token"]

@pytest.fixture(scope="session")
def auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"}
