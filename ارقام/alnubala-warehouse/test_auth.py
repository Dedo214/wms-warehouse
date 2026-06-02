"""Tests — Authentication"""
import json

def test_login_success(client):
    r = client.post("/api/auth/login",
                    json={"username":"admin","password":"admin123"})
    d = json.loads(r.data)
    assert r.status_code == 200
    assert d["success"] is True
    assert "access_token" in d["data"]
    assert d["data"]["user"]["role"] == "admin"

def test_login_wrong_password(client):
    r = client.post("/api/auth/login",
                    json={"username":"admin","password":"wrong"})
    assert r.status_code == 401
    assert json.loads(r.data)["success"] is False

def test_login_wrong_user(client):
    r = client.post("/api/auth/login",
                    json={"username":"nobody","password":"test"})
    assert r.status_code == 401

def test_login_missing_fields(client):
    r = client.post("/api/auth/login", json={})
    assert r.status_code == 400

def test_me_authenticated(client, admin_token):
    r = client.get("/api/auth/me",
                   headers={"Authorization": f"Bearer {admin_token}"})
    d = json.loads(r.data)
    assert r.status_code == 200
    assert d["data"]["user"]["username"] == "admin"

def test_me_unauthenticated(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401

def test_register_new_user(client):
    r = client.post("/api/auth/register",
                    json={"name":"مستخدم اختبار",
                          "username":"pytest_user",
                          "password":"pytest123"})
    d = json.loads(r.data)
    assert r.status_code == 201
    assert d["success"] is True
    assert "access_token" in d["data"]

def test_register_duplicate_username(client):
    client.post("/api/auth/register",
                json={"name":"تكرار","username":"dup_user","password":"test1234"})
    r = client.post("/api/auth/register",
                    json={"name":"تكرار2","username":"dup_user","password":"test1234"})
    assert r.status_code == 400

def test_register_short_password(client):
    r = client.post("/api/auth/register",
                    json={"name":"قصير","username":"shortpw","password":"abc"})
    assert r.status_code == 400

def test_change_password(client, admin_token):
    r = client.post("/api/auth/change-password",
                    json={"old_password":"admin123","new_password":"admin12345"},
                    headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    # Restore original password
    client.post("/api/auth/change-password",
                json={"old_password":"admin12345","new_password":"admin123"},
                headers={"Authorization": f"Bearer {admin_token}"})

def test_health(client):
    r = client.get("/health")
    d = json.loads(r.data)
    assert r.status_code == 200
    assert d["status"] == "ok"
