"""Tests — Transfers"""
import json

def _setup(client, auth):
    items = json.loads(client.get("/api/items", headers=auth).data)["data"]["items"]
    whs   = json.loads(client.get("/api/warehouses", headers=auth).data)["data"]
    iid   = items[3]["id"]
    wh1   = whs[0]["id"]
    wh2   = whs[1]["id"]
    # ensure enough stock
    client.post("/api/movements",
                json={"type":"in","item_id":iid,"warehouse_id":wh1,"quantity":200},
                headers=auth)
    return iid, wh1, wh2

def _deactivate_chains(client, auth):
    """Deactivate any active transfer approval chains so transfers don't auto-assign"""
    r = client.get("/api/approval/chains?target_type=transfer", headers=auth)
    for c in json.loads(r.data)["data"]:
        if c.get("is_active"):
            client.put(f"/api/approval/chains/{c['id']}",
                       json={"is_active": False}, headers=auth)

def test_transfers_list(client, auth):
    r = client.get("/api/transfers", headers=auth)
    assert r.status_code == 200

def test_create_transfer(client, auth):
    iid, wh1, wh2 = _setup(client, auth)
    r = client.post("/api/transfers",
                    json={"item_id":iid,"from_warehouse_id":wh1,
                          "to_warehouse_id":wh2,"quantity":20,
                          "reason":"اختبار pytest"},
                    headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 201
    assert d["data"]["status"] == "pending"
    return d["data"]["id"]

def test_approve_transfer(client, auth):
    _deactivate_chains(client, auth)
    iid, wh1, wh2 = _setup(client, auth)
    r = client.post("/api/transfers",
                    json={"item_id":iid,"from_warehouse_id":wh1,
                          "to_warehouse_id":wh2,"quantity":10,
                          "reason":"للاعتماد"},
                    headers=auth)
    tid = json.loads(r.data)["data"]["id"]
    r2  = client.post(f"/api/transfers/{tid}/approve", json={}, headers=auth)
    d2  = json.loads(r2.data)
    assert r2.status_code == 200
    assert d2["data"]["status"] == "executed"

def test_reject_transfer(client, auth):
    iid, wh1, wh2 = _setup(client, auth)
    r = client.post("/api/transfers",
                    json={"item_id":iid,"from_warehouse_id":wh1,
                          "to_warehouse_id":wh2,"quantity":5,
                          "reason":"للرفض"},
                    headers=auth)
    tid = json.loads(r.data)["data"]["id"]
    r2  = client.post(f"/api/transfers/{tid}/reject",
                      json={"reason":"اختبار الرفض"},
                      headers=auth)
    d2  = json.loads(r2.data)
    assert r2.status_code == 200
    assert d2["data"]["status"] == "rejected"

def test_same_warehouse_rejected(client, auth):
    iid, wh1, _ = _setup(client, auth)
    r = client.post("/api/transfers",
                    json={"item_id":iid,"from_warehouse_id":wh1,
                          "to_warehouse_id":wh1,"quantity":5,
                          "reason":"خطأ"},
                    headers=auth)
    assert r.status_code == 400

def test_transfer_filter_status(client, auth):
    r = client.get("/api/transfers?status=pending", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    for t in d["data"]:
        assert t["status"] == "pending"
