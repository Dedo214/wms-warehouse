"""Tests — Reports & Export"""
import json
from datetime import datetime

def test_report_balance(client, auth):
    r = client.get("/api/reports/balance", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert "rows" in d["data"]
    assert "warehouses" in d["data"]
    assert len(d["data"]["rows"]) >= 12

def test_report_daily(client, auth):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = client.get(f"/api/reports/daily?date={today}", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert "movements" in d["data"]
    assert "summary" in d["data"]

def test_report_daily_bad_date(client, auth):
    r = client.get("/api/reports/daily?date=BADDATE", headers=auth)
    assert r.status_code == 400

def test_report_transfers(client, auth):
    r = client.get("/api/reports/transfers", headers=auth)
    d = json.loads(r.data)
    assert r.status_code == 200
    assert "summary" in d["data"]
    s = d["data"]["summary"]
    assert "total" in s and "pending" in s

def test_export_excel_balance(client, auth):
    r = client.get("/api/export/excel?type=balance", headers=auth)
    assert r.status_code == 200
    assert "spreadsheet" in r.content_type

def test_export_excel_movements(client, auth):
    r = client.get("/api/export/excel?type=movements", headers=auth)
    assert r.status_code == 200

def test_export_csv_balance(client, auth):
    r = client.get("/api/export/csv?type=balance", headers=auth)
    assert r.status_code == 200
    assert "csv" in r.content_type.lower()

def test_export_csv_movements(client, auth):
    r = client.get("/api/export/csv?type=movements", headers=auth)
    assert r.status_code == 200

def test_export_pdf(client, auth):
    r = client.get("/api/export/pdf", headers=auth)
    assert r.status_code == 200
    assert "pdf" in r.content_type.lower()

def test_backup_json(client, auth):
    r = client.get("/api/backup", headers=auth)
    assert r.status_code == 200
    assert "json" in r.content_type.lower()
    d = json.loads(r.data)
    assert "warehouses" in d
    assert "items" in d
    assert "movements" in d
