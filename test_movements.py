"""Tests — Stock Movements"""
import json

def _setup(client, auth):
    items = json.loads(client.get("/api/items", headers=auth).data)["data"]["items"]
    whs   = json.loads(client.get("/api/warehouses", headers=auth).data)["data"]
    return items[3]["id"], whs[0]["id"], whs[1]["id"]

def test_movements_list(client, auth):
    r = client.get("/api/movements", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert "movements" in d["data"]
    assert "total" in d["data"]

def test_create_movement_in(client, auth):
    iid, wh1, _ = _setup(client, auth)
    r = client.post("/api/movements",
                    json={"type":"in","item_id":iid,
                          "warehouse_id":wh1,"quantity":100,"unit_price":50},
                    headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 201
    assert d["data"]["type"] == "in"
    assert d["data"]["quantity"] == 100

def test_create_movement_out(client, auth):
    iid, wh1, _ = _setup(client, auth)
    r = client.post("/api/movements",
                    json={"type":"out","item_id":iid,
                          "warehouse_id":wh1,"quantity":5},
                    headers=auth)
    assert r.status_code == 201

def test_movement_overstock_rejected(client, auth):
    iid, wh1, _ = _setup(client, auth)
    r = client.post("/api/movements",
                    json={"type":"out","item_id":iid,
                          "warehouse_id":wh1,"quantity":9999999},
                    headers=auth)
    assert r.status_code == 400

def test_movement_zero_qty_rejected(client, auth):
    iid, wh1, _ = _setup(client, auth)
    r = client.post("/api/movements",
                    json={"type":"in","item_id":iid,
                          "warehouse_id":wh1,"quantity":0},
                    headers=auth)
    assert r.status_code == 400

def test_movements_filter_by_type(client, auth):
    r = client.get("/api/movements?type=in", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    for m in d["data"]["movements"]:
        assert m["type"] == "in"

def test_movements_pagination(client, auth):
    r = client.get("/api/movements?page=1&per_page=5", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert len(d["data"]["movements"]) <= 5
