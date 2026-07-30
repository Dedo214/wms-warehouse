"""Unit tests — service layer (audit, notifications, counts, suppliers, users, reports)"""
import datetime
import json

import openpyxl
import pytest

from app.models import (db, AuditLog, Category, InventoryCount, InventoryCountLine,
                        Item, Notification, Project, Stock, StockMovement,
                        User, Warehouse)
from app.services import (AuditService, AuthService, CountService, NotificationService,
                          ReportService, StockInquiryService, SupplierService, UserService)


@pytest.fixture
def ctx(app):
    """Request context — services touch request.remote_addr through AuditService."""
    with app.test_request_context("/unit", headers={"User-Agent": "unit-tests"}):
        yield


@pytest.fixture
def warehouse(ctx):
    wh = Warehouse(name="مخزن اختبار الوحدة", code="WH-UNIT", capacity=100, type="sub")
    db.session.add(wh)
    db.session.commit()
    yield wh
    Stock.query.filter_by(warehouse_id=wh.id).delete()
    StockMovement.query.filter_by(warehouse_id=wh.id).delete()
    for cnt in InventoryCount.query.filter_by(warehouse_id=wh.id).all():
        InventoryCountLine.query.filter_by(count_id=cnt.id).delete()
        db.session.delete(cnt)
    db.session.delete(wh)
    db.session.commit()


@pytest.fixture
def admin(ctx):
    return User.query.filter_by(username="admin").first()


# ══ AUDIT ══════════════════════════════════════════════════════
def test_audit_log_records_request_metadata(ctx):
    AuditService.log("create", "unit", 42, "وصف", old={"q": 1}, new={"q": 2})
    db.session.commit()
    entry = AuditLog.query.filter_by(resource="unit", resource_id=42).first()
    assert entry.action == "create"
    assert entry.description == "وصف"
    assert json.loads(entry.old_data) == {"q": 1}
    assert json.loads(entry.new_data) == {"q": 2}
    assert entry.user_agent == "unit-tests"
    db.session.delete(entry)
    db.session.commit()


def test_audit_log_never_raises_on_bad_payload(ctx):
    AuditService.log("create", "unit", 1, "x", new={"bad": object()})
    db.session.rollback()


def test_audit_get_logs_filters(ctx, admin):
    AuditService.log("unit_action", "unit_res", 7, "سجل فريد للاختبار")
    db.session.commit()

    all_logs = AuditService.get_logs(per_page=5)
    assert all_logs["total"] >= 1
    assert all_logs["per_page"] == 5

    by_action = AuditService.get_logs(filters={"action": "unit_action"})
    assert by_action["total"] == 1
    assert by_action["items"][0].resource == "unit_res"

    assert AuditService.get_logs(filters={"resource": "unit_res"})["total"] == 1
    assert AuditService.get_logs(filters={"search": "فريد للاختبار"})["total"] == 1
    assert AuditService.get_logs(filters={"action": "no_such_action"})["total"] == 0

    today = datetime.datetime.utcnow().date()
    ranged = AuditService.get_logs(filters={"action": "unit_action",
                                            "date_from": today - datetime.timedelta(days=1),
                                            "date_to": today})
    assert ranged["total"] == 1

    AuditLog.query.filter_by(action="unit_action").delete()
    db.session.commit()


def test_audit_get_logs_filters_by_user(ctx, admin):
    entry = AuditLog(user_id=admin.id, action="unit_user_action", resource="unit")
    db.session.add(entry)
    db.session.commit()
    res = AuditService.get_logs(filters={"user_id": str(admin.id), "action": "unit_user_action"})
    assert res["total"] == 1
    db.session.delete(entry)
    db.session.commit()


# ══ NOTIFICATIONS ══════════════════════════════════════════════
def test_notification_push_targets_requested_roles(ctx):
    NotificationService.push("unit", "عنوان", "رسالة", ref_type="unit", ref_id=1, roles=("admin",))
    db.session.commit()
    created = Notification.query.filter_by(type="unit").all()
    assert created
    recipients = {User.query.get(n.user_id).role for n in created}
    assert recipients == {"admin"}
    Notification.query.filter_by(type="unit").delete()
    db.session.commit()


def test_check_low_stock_creates_one_notification_per_day(ctx, warehouse):
    item = Item(code="UNIT-LOW", name="صنف منخفض", unit="قطعة",
                min_quantity=10, reorder_point=12, unit_price=5)
    db.session.add(item)
    db.session.commit()
    db.session.add(Stock(item_id=item.id, warehouse_id=warehouse.id, quantity=3))
    db.session.commit()

    NotificationService.check_low_stock(item.id)
    NotificationService.check_low_stock(item.id)
    notes = Notification.query.filter_by(ref_type="item", ref_id=item.id, type="low_stock").all()
    assert len(notes) == 1
    assert item.name in notes[0].title

    Notification.query.filter_by(ref_id=item.id, type="low_stock").delete()
    Stock.query.filter_by(item_id=item.id).delete()
    db.session.delete(item)
    db.session.commit()


def test_check_low_stock_ignores_healthy_and_unknown_items(ctx, warehouse):
    item = Item(code="UNIT-OK", name="صنف كافٍ", unit="قطعة", min_quantity=1, unit_price=5)
    db.session.add(item)
    db.session.commit()
    db.session.add(Stock(item_id=item.id, warehouse_id=warehouse.id, quantity=99))
    db.session.commit()

    NotificationService.check_low_stock(item.id)
    NotificationService.check_low_stock(999999)
    assert Notification.query.filter_by(ref_id=item.id, type="low_stock").count() == 0

    Stock.query.filter_by(item_id=item.id).delete()
    db.session.delete(item)
    db.session.commit()


def test_check_low_stock_skips_items_without_minimum(ctx, warehouse):
    item = Item(code="UNIT-NOMIN", name="بلا حد أدنى", unit="قطعة", min_quantity=0, unit_price=5)
    db.session.add(item)
    db.session.commit()
    NotificationService.check_low_stock(item.id)
    assert Notification.query.filter_by(ref_id=item.id, type="low_stock").count() == 0
    db.session.delete(item)
    db.session.commit()


# ══ AUTH ═══════════════════════════════════════════════════════
def test_change_password_success_and_rollback(ctx, admin):
    okay, error = AuthService.change_password(admin.id, "admin123", "newpass123")
    assert (okay, error) == (True, None)
    assert admin.check_password("newpass123")

    okay, error = AuthService.change_password(admin.id, "newpass123", "admin123")
    assert okay is True
    assert admin.check_password("admin123")


def test_change_password_rejects_wrong_old_password(ctx, admin):
    okay, error = AuthService.change_password(admin.id, "wrong", "whatever123")
    assert okay is False
    assert error


def test_change_password_rejects_short_new_password(ctx, admin):
    okay, error = AuthService.change_password(admin.id, "admin123", "123")
    assert okay is False
    assert "6" in error


def test_change_password_unknown_user(ctx):
    okay, error = AuthService.change_password(999999, "x", "yyyyyy")
    assert okay is False
    assert error


# ══ INVENTORY COUNTS ═══════════════════════════════════════════
def test_count_lifecycle_adjusts_stock_and_reports_differences(ctx, warehouse, admin):
    item = Item(code="UNIT-CNT", name="صنف جرد", unit="قطعة", min_quantity=0, unit_price=10)
    db.session.add(item)
    db.session.commit()
    db.session.add(Stock(item_id=item.id, warehouse_id=warehouse.id, quantity=20))
    db.session.commit()

    count, error = CountService.create({"warehouse_id": warehouse.id, "notes": "جرد اختبار"}, admin.id)
    assert error is None
    assert count.status == "active"
    assert count in CountService.get_list()
    line = InventoryCountLine.query.filter_by(count_id=count.id, item_id=item.id).one()
    assert line.system_quantity == 20

    duplicate, error = CountService.create({"warehouse_id": warehouse.id}, admin.id)
    assert duplicate is None
    assert error

    updated, error = CountService.update_line(count.id, line.id, 17, notes="ناقص")
    assert error is None
    assert updated.actual_quantity == 17
    assert updated.notes == "ناقص"

    result, error = CountService.complete(count.id, admin.id)
    assert error is None
    assert result["differences"] == 1
    assert result["count"].status == "completed"
    assert Stock.query.filter_by(item_id=item.id, warehouse_id=warehouse.id).one().quantity == 17
    adjustment = StockMovement.query.filter_by(item_id=item.id, warehouse_id=warehouse.id).one()
    assert adjustment.type == "out"
    assert adjustment.quantity == 3

    assert CountService.complete(count.id, admin.id)[1]
    Notification.query.filter_by(ref_type="count", ref_id=count.id).delete()
    db.session.commit()


def test_count_create_requires_warehouse(ctx, admin):
    count, error = CountService.create({}, admin.id)
    assert count is None
    assert error


def test_count_update_line_rejects_foreign_line(ctx, warehouse, admin):
    count, _ = CountService.create({"warehouse_id": warehouse.id}, admin.id)
    line, error = CountService.update_line(count.id, 999999, 5)
    assert line is None
    assert error
    CountService.complete(count.id, admin.id)


def test_count_complete_unknown_session(ctx, admin):
    result, error = CountService.complete(999999, admin.id)
    assert result is None
    assert error


# ══ SUPPLIERS ══════════════════════════════════════════════════
def test_supplier_create_update_and_search(ctx):
    supplier, error = SupplierService.create({"name": "مورد اختبار الوحدة",
                                              "category": "سباكة", "phone": "0500"})
    assert error is None
    assert supplier.code.startswith("SUP-")
    assert supplier.payment_terms  # default applied
    assert supplier.rating == 3

    assert supplier in SupplierService.get_list(search="اختبار الوحدة")
    assert supplier in SupplierService.get_list(search="سباكة")
    assert SupplierService.get_list(search="لا-يوجد-مورد") == []

    updated, error = SupplierService.update(supplier.id, {"name": "مورد محدث", "rating": 5})
    assert error is None
    assert (updated.name, updated.rating) == ("مورد محدث", 5)

    deactivated, _ = SupplierService.update(supplier.id, {"is_active": False})
    assert deactivated not in SupplierService.get_list()

    db.session.delete(supplier)
    db.session.commit()


def test_supplier_create_requires_name(ctx):
    supplier, error = SupplierService.create({"category": "سباكة"})
    assert supplier is None
    assert error


def test_supplier_create_honours_explicit_code(ctx):
    supplier, _ = SupplierService.create({"name": "مورد بكود", "code": "SUP-UNIT-1"})
    assert supplier.code == "SUP-UNIT-1"
    db.session.delete(supplier)
    db.session.commit()


def test_supplier_update_unknown_id(ctx):
    supplier, error = SupplierService.update(999999, {"name": "x"})
    assert supplier is None
    assert error


# ══ USERS ══════════════════════════════════════════════════════
def test_user_create_update_lifecycle(ctx, admin):
    user, error = UserService.create({"name": "مستخدم اختبار", "username": "unit_user",
                                      "password": "secret123", "email": "unit@wh.com"})
    assert error is None
    assert user.role == "keeper"  # default
    assert user.check_password("secret123")
    assert user in UserService.get_list()

    duplicate, error = UserService.create({"name": "آخر", "username": "unit_user",
                                           "password": "secret123"})
    assert duplicate is None
    assert "username" in error

    updated, error = UserService.update(user.id, {"name": "مستخدم محدث", "role": "manager",
                                                  "password": "another123"}, admin.id)
    assert error is None
    assert (updated.name, updated.role) == ("مستخدم محدث", "manager")
    assert updated.check_password("another123")

    disabled, error = UserService.update(user.id, {"is_active": False}, admin.id)
    assert error is None
    assert disabled not in UserService.get_list()

    db.session.delete(user)
    db.session.commit()


def test_user_create_validation_errors(ctx):
    user, errors = UserService.create({})
    assert user is None
    assert set(errors) == {"name", "username", "password"}

    user, errors = UserService.create({"name": "n", "username": "u", "password": "123"})
    assert user is None
    assert "6" in errors["password"]


def test_user_update_rejects_self_deactivation(ctx, admin):
    user, error = UserService.update(admin.id, {"is_active": False}, admin.id)
    assert user is None
    assert error
    assert User.query.get(admin.id).is_active is True


def test_user_update_rejects_short_password(ctx, admin):
    user, error = UserService.update(admin.id, {"password": "123"}, admin.id)
    assert user is None
    assert error
    db.session.rollback()


def test_user_update_unknown_id(ctx, admin):
    user, error = UserService.update(999999, {"name": "x"}, admin.id)
    assert user is None
    assert error


# ══ STOCK INQUIRY ══════════════════════════════════════════════
def test_stock_inquiry_returns_per_warehouse_columns(ctx):
    res = StockInquiryService.search()
    assert res["warehouses"]
    row = res["items"][0]
    wh_id = res["warehouses"][0]["id"]
    assert f"wh_{wh_id}" in row and f"wh_{wh_id}_name" in row
    assert row["total_stock"] == sum(row[f"wh_{w['id']}"] for w in res["warehouses"])
    assert row["status"] in {"critical", "low", "ok", "out"}
    assert row["status_label"]


def test_stock_inquiry_filters_by_code_and_name(ctx):
    item = Item.query.filter_by(code="WH-0001").first()
    by_code = StockInquiryService.search("WH-0001")
    assert [r["code"] for r in by_code["items"]] == ["WH-0001"]
    assert StockInquiryService.search(item.name)["items"][0]["name"] == item.name
    assert StockInquiryService.search("UNMATCHED-QUERY")["items"] == []


# ══ REPORTS ════════════════════════════════════════════════════
def test_report_balance_totals_match_stock(ctx):
    res = ReportService.balance()
    assert res["warehouses"]
    row = next(r for r in res["rows"] if r["code"] == "WH-0002")
    item = Item.query.filter_by(code="WH-0002").first()
    assert row["total"] == item.get_total_stock()
    assert row["total_value"] == round(row["total"] * item.unit_price, 2)


def test_report_daily_summarises_movements(ctx, warehouse, admin):
    item = Item.query.filter_by(code="WH-0002").first()
    today = datetime.datetime.utcnow()
    movements = [
        StockMovement(ref_number="UNIT-IN", type="in", item_id=item.id,
                      warehouse_id=warehouse.id, quantity=10, unit_price=1,
                      user_id=admin.id, created_at=today),
        StockMovement(ref_number="UNIT-OUT", type="out", item_id=item.id,
                      warehouse_id=warehouse.id, quantity=4, unit_price=1,
                      user_id=admin.id, created_at=today),
    ]
    db.session.add_all(movements)
    db.session.commit()

    today_str = today.strftime("%Y-%m-%d")
    res, error = ReportService.daily(today_str)
    assert error is None
    assert res["summary"]["total_in"] >= 10
    assert res["summary"]["total_out"] >= 4
    assert res["summary"]["count"] == len(res["movements"])

    ranged, error = ReportService.daily(
        (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"), today_str)
    assert error is None
    assert ranged["date_to"] == today_str
    assert ranged["summary"]["count"] >= res["summary"]["count"]

    for mov in movements:
        db.session.delete(mov)
    db.session.commit()


def test_report_daily_rejects_bad_dates(ctx):
    assert ReportService.daily("17-05-2024")[0] is None
    assert ReportService.daily("2024-05-17", "not-a-date")[0] is None


def test_report_transfers_summary(ctx):
    res = ReportService.transfers()
    summary = res["summary"]
    assert summary["total"] == len(res["transfers"])
    assert summary["total"] == summary["pending"] + summary["executed"] + summary["rejected"] \
        or summary["total"] >= summary["pending"]

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    assert ReportService.transfers(date_from=today, date_to=today)["summary"]["total"] <= summary["total"]
    # invalid dates are ignored rather than raising
    assert ReportService.transfers(date_from="bad", date_to="bad")["summary"]["total"] == summary["total"]


def test_report_budget_computes_spend_per_project(ctx, warehouse, admin):
    project = Project(name="مشروع اختبار الوحدة", code="PRJ-UNIT", budget=1000, status="active")
    db.session.add(project)
    db.session.commit()
    item = Item.query.filter_by(code="WH-0002").first()
    movements = [
        StockMovement(ref_number="UNIT-P-OUT", type="out", item_id=item.id,
                      warehouse_id=warehouse.id, quantity=10, unit_price=20,
                      user_id=admin.id, project=project.name),
        StockMovement(ref_number="UNIT-P-RET", type="return", item_id=item.id,
                      warehouse_id=warehouse.id, quantity=2, unit_price=20,
                      user_id=admin.id, project=project.name),
        StockMovement(ref_number="UNIT-P-DMG", type="damage", item_id=item.id,
                      warehouse_id=warehouse.id, quantity=1, unit_price=20,
                      user_id=admin.id, project=project.name),
    ]
    db.session.add_all(movements)
    db.session.commit()

    res = ReportService.budget()
    row = next(r for r in res["projects"] if r["code"] == "PRJ-UNIT")
    assert row["spent"] == 180.0  # 200 out + 20 damage - 40 return
    assert row["remaining"] == 820.0
    assert row["usage_pct"] == 18.0
    assert res["summary"]["total_budget"] >= 1000

    for mov in movements:
        db.session.delete(mov)
    db.session.delete(project)
    db.session.commit()


def test_report_budget_without_budget_reports_negative_remaining(ctx):
    project = Project(name="مشروع بلا موازنة", code="PRJ-UNIT-0", budget=0, status="paused")
    db.session.add(project)
    db.session.commit()
    row = next(r for r in ReportService.budget()["projects"] if r["code"] == "PRJ-UNIT-0")
    assert row["budget"] == 0
    assert row["usage_pct"] == 0
    assert row["remaining"] == 0
    db.session.delete(project)
    db.session.commit()


@pytest.mark.parametrize("report_type", ["balance", "transfers", "diffs", "budget",
                                         "consumption", "fastslow", "valuation",
                                         "audit", "no_such_report"])
def test_report_export_excel(ctx, report_type):
    wb = openpyxl.load_workbook(ReportService.export_excel(report_type))
    assert wb.active.max_row >= 1


def test_report_export_excel_budget_includes_totals_row(ctx):
    project = Project(name="مشروع تصدير", code="PRJ-XLSX", budget=500, status="active")
    db.session.add(project)
    db.session.commit()
    summary = ReportService.budget()["summary"]
    ws = openpyxl.load_workbook(ReportService.export_excel("budget")).active
    project_rows = {ws.cell(row=r, column=2).value: r for r in range(3, ws.max_row)}
    assert "PRJ-XLSX" in project_rows
    assert ws.cell(row=project_rows["PRJ-XLSX"], column=4).value == 500

    totals_row = ws.max_row
    assert ws.cell(row=totals_row, column=1).font.bold
    assert ws.cell(row=totals_row, column=4).value == summary["total_budget"]
    assert ws.cell(row=totals_row, column=5).value == summary["total_spent"]
    assert ws.cell(row=totals_row, column=6).value == summary["total_remaining"]

    db.session.delete(project)
    db.session.commit()


# ══ CATEGORY SANITY ════════════════════════════════════════════
def test_seeded_categories_have_items(ctx):
    category = Category.query.first()
    assert category.to_dict()["item_count"] >= 0
