"""Tests — Items & Stock"""
import json

def _get_whs(client, auth):
    return json.loads(client.get("/api/warehouses", headers=auth).data)["data"]

def test_items_list(client, auth):
    r = client.get("/api/items", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert d["data"]["total"] >= 12   # seeded 12

def test_items_search(client, auth):
    r = client.get("/api/items?search=حديد", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert d["data"]["total"] >= 1

def test_items_filter_critical(client, auth):
    r = client.get("/api/items?status=critical", headers=auth)
    assert r.status_code == 200

def test_item_detail(client, auth):
    items = json.loads(client.get("/api/items", headers=auth).data)["data"]["items"]
    iid = items[0]["id"]
    r = client.get(f"/api/items/{iid}", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert "warehouse_stocks" in d["data"]
    assert "last_movements" in d["data"]

def test_scan_barcode(client, auth):
    items = json.loads(client.get("/api/items", headers=auth).data)["data"]["items"]
    bc = items[0]["barcode"]
    r = client.get(f"/api/items/scan/{bc}", headers=auth)
    assert r.status_code == 200

def test_scan_not_found(client, auth):
    r = client.get("/api/items/scan/INVALID_CODE_XYZ", headers=auth)
    assert r.status_code == 404

def test_create_item(client, auth):
    whs = _get_whs(client, auth)
    wh_id = whs[0]["id"]
    r = client.post("/api/items",
                    json={"name":"صنف بايثون اختبار","code":"PYT-001",
                          "unit":"قطعة","min_quantity":10,"unit_price":150,
                          "initial_stocks":{str(wh_id):50}},
                    headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 201
    assert d["data"]["code"] == "PYT-001"

def test_create_item_duplicate_code(client, auth):
    r = client.post("/api/items",
                    json={"name":"مكرر","code":"PYT-001","unit":"قطعة"},
                    headers=auth)
    assert r.status_code == 400

def test_create_item_missing_fields(client, auth):
    r = client.post("/api/items", json={"name":"بدون كود"}, headers=auth)
    assert r.status_code == 400

def test_update_item(client, auth):
    items = json.loads(client.get("/api/items", headers=auth).data)["data"]["items"]
    iid = items[0]["id"]
    r = client.put(f"/api/items/{iid}",
                   json={"description":"وصف تحديث اختبار"},
                   headers=auth)
    assert r.status_code == 200
