"""Tests — Dashboard"""
import json

def test_dashboard_structure(client, auth):
    r = client.get("/api/dashboard", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert "kpis" in d["data"]
    assert "warehouses" in d["data"]
    assert "chart_data" in d["data"]
    assert len(d["data"]["chart_data"]) == 7

def test_dashboard_kpis(client, auth):
    r = client.get("/api/dashboard", headers=auth)
    k = json.loads(r.data)["data"]["kpis"]
    assert k["total_items"] >= 0
    assert k["total_movements"] >= 0
    assert k["pending_transfers"] >= 0
    assert k["total_value"] >= 0

def test_dashboard_requires_auth(client):
    r = client.get("/api/dashboard")
    assert r.status_code == 401

def test_warehouses_in_dashboard(client, auth):
    r = client.get("/api/dashboard", headers=auth)
    whs = json.loads(r.data)["data"]["warehouses"]
    assert len(whs) == 3
    for wh in whs:
        assert "name" in wh
        assert "item_count" in wh
