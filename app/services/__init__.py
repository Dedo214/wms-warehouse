"""
ط·ط¨ظ‚ط© ط§ظ„ط®ط¯ظ…ط§طھ â€” Business Logic Services
ظƒظ„ ط§ظ„ظ…ظ†ط·ظ‚ ط§ظ„طھط¬ط§ط±ظٹ ظ…ط¹ط²ظˆظ„ ظ‡ظ†ط§ ط¨ط¹ظٹط¯ط§ظ‹ ط¹ظ† ط§ظ„ظ€ routes
"""
import datetime, json, calendar
from sqlalchemy import func
from flask import request, current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import (db, User, Warehouse, Category, Supplier, Item,
                         Stock, StockMovement, Transfer, InventoryCount,
                         InventoryCountLine, Notification, AuditLog, Project,
                         PurchaseRequest, PRItem, ApprovalLog,
                         RFQ, RFQSupplier, Quotation, QuotationItem,
                         PurchaseOrder, POItem,
                         GoodsReceipt, GRNItem,
                         PurchaseReturn, PReturnItem,
                         SupplierEvaluation, SupplierProfile, InventoryLayer,
                         ApprovalChain)
from app.utils import gen_ref, paginate, parse_date

# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  AUDIT SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class AuditService:
    @staticmethod
    def log(action, resource=None, resource_id=None, desc="", old=None, new=None):
        try:
            uid = None
            try:
                verify_jwt_in_request(optional=True)
                uid = get_jwt_identity()
            except Exception:
                pass
            entry = AuditLog(
                user_id     = uid,
                action      = action,
                resource    = resource,
                resource_id = resource_id,
                description = desc,
                old_data    = json.dumps(old, ensure_ascii=False) if old else None,
                new_data    = json.dumps(new, ensure_ascii=False) if new else None,
                ip_address  = request.remote_addr,
                user_agent  = request.headers.get("User-Agent", "")[:300],
            )
            db.session.add(entry)
        except Exception:
            pass  # never crash on audit

    @staticmethod
    def get_logs(page=1, per_page=50, filters=None):
        q = AuditLog.query
        if filters:
            if filters.get("user_id"):
                q = q.filter(AuditLog.user_id == int(filters["user_id"]))
            if filters.get("action"):
                q = q.filter(AuditLog.action == filters["action"])
            if filters.get("resource"):
                q = q.filter(AuditLog.resource == filters["resource"])
            if filters.get("date_from"):
                q = q.filter(AuditLog.created_at >= filters["date_from"])
            if filters.get("date_to"):
                q = q.filter(AuditLog.created_at <= filters["date_to"] + datetime.timedelta(days=1))
            if filters.get("search"):
                q = q.filter(AuditLog.description.ilike(f'%{filters["search"]}%'))
        q = q.order_by(AuditLog.created_at.desc())
        return paginate(q, page, per_page)


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  NOTIFICATION SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class NotificationService:
    @staticmethod
    def push(type_, title, message, ref_type=None, ref_id=None, roles=("admin","manager")):
        users = User.query.filter(User.role.in_(roles), User.is_active == True).all()
        user_ids = []
        for u in users:
            db.session.add(Notification(
                type=type_, title=title, message=message,
                user_id=u.id, ref_type=ref_type, ref_id=ref_id,
            ))
            user_ids.append(u.id)
        try:
            from app import get_socketio
            sio = get_socketio()
            for uid in user_ids:
                sio.emit("notification_update", {"unread": 1}, to=f"user_{uid}")
        except Exception:
            pass

    @staticmethod
    def check_low_stock(item_id):
        item = Item.query.get(item_id)
        if not item or item.min_quantity <= 0:
            return
        total = item.get_total_stock()
        if total <= item.min_quantity:
            today = datetime.datetime.utcnow().date()
            exists = Notification.query.filter(
                Notification.ref_type == "item",
                Notification.ref_id   == item_id,
                Notification.type     == "low_stock",
                func.date(Notification.created_at) == today,
            ).first()
            if not exists:
                NotificationService.push(
                    "low_stock",
                    f"âڑ ï¸ڈ ظ…ط®ط²ظˆظ† ظ…ظ†ط®ظپط¶: {item.name}",
                    f"ط§ظ„ط±طµظٹط¯ ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹ {total} {item.unit} â€” ط§ظ„ط­ط¯ ط§ظ„ط£ط¯ظ†ظ‰ {item.min_quantity}",
                    ref_type="item", ref_id=item_id,
                )
                db.session.commit()


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  AUTH SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class AuthService:
    @staticmethod
    def login(username, password):
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        if not user or not user.check_password(password):
            AuditService.log("login_failed", "auth", desc=f"ظپط´ظ„ ط¯ط®ظˆظ„: {username}")
            db.session.commit()
            return None, "ط¨ظٹط§ظ†ط§طھ طھط³ط¬ظٹظ„ ط§ظ„ط¯ط®ظˆظ„ ط؛ظٹط± طµط­ظٹط­ط©"
        if not user.is_active:
            return None, "ط§ظ„ط­ط³ط§ط¨ ظ…ظˆظ‚ظˆظپ â€” طھظˆط§طµظ„ ظ…ط¹ ط§ظ„ظ…ط³ط¤ظˆظ„"
        user.last_login = datetime.datetime.utcnow()
        AuditService.log("login", "auth", user.id, f"ط¯ط®ظˆظ„: {user.name}")
        db.session.commit()
        return user, None

    @staticmethod
    def change_password(user_id, old_pw, new_pw):
        user = User.query.get(user_id)
        if not user:
            return False, "ط§ظ„ظ…ط³طھط®ط¯ظ… ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        if not user.check_password(old_pw):
            return False, "ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط­ط§ظ„ظٹط© ط؛ظٹط± طµط­ظٹط­ط©"
        if len(new_pw) < 6:
            return False, "ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظٹط¬ط¨ ط£ظ† طھظƒظˆظ† 6 ط£ط­ط±ظپ ط¹ظ„ظ‰ ط§ظ„ط£ظ‚ظ„"
        user.set_password(new_pw)
        AuditService.log("update", "user", user_id, "طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±")
        db.session.commit()
        return True, None


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  DASHBOARD SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class DashboardService:
    @staticmethod
    def get_data(user_id):
        today = datetime.datetime.utcnow().date()
        whs   = Warehouse.query.filter_by(is_active=True).all()
        items = Item.query.filter_by(is_active=True).all()

        today_movs = StockMovement.query.filter(
            func.date(StockMovement.created_at) == today
        ).all()

        total_value    = 0.0
        critical_items = []
        for item in items:
            total = item.get_total_stock()
            total_value += total * item.unit_price
            st = item.get_status()
            if st in ("critical", "warning"):
                critical_items.append({
                    "id":item.id,"name":item.name,"total":total,
                    "min":item.min_quantity,"unit":item.unit,"status":st,
                })

        wh_stats = []
        for wh in whs:
            ic = db.session.query(func.count(Stock.id)).filter(
                Stock.warehouse_id == wh.id, Stock.quantity > 0
            ).scalar() or 0
            wm = [m for m in today_movs if m.warehouse_id == wh.id]
            wh_stats.append({
                "id":wh.id,"name":wh.name,"type":wh.type,
                "location":wh.location,"item_count":ic,"capacity":wh.capacity,
                "today_in": sum(m.quantity for m in wm if m.type=="in"),
                "today_out":sum(m.quantity for m in wm if m.type=="out"),
            })

        # 7-day chart
        chart = []
        day_names = ["ط§ظ„ط¥ط«ظ†ظٹظ†","ط§ظ„ط«ظ„ط§ط«ط§ط،","ط§ظ„ط£ط±ط¨ط¹ط§ط،","ط§ظ„ط®ظ…ظٹط³","ط§ظ„ط¬ظ…ط¹ط©","ط§ظ„ط³ط¨طھ","ط§ظ„ط£ط­ط¯"]
        for i in range(6, -1, -1):
            d  = (datetime.datetime.utcnow() - datetime.timedelta(days=i)).date()
            dm = StockMovement.query.filter(func.date(StockMovement.created_at)==d).all()
            chart.append({
                "date": day_names[d.weekday()],
                "in":   sum(m.quantity for m in dm if m.type=="in"),
                "out":  sum(m.quantity for m in dm if m.type=="out"),
            })

        recent   = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(10).all()
        pending  = Transfer.query.filter_by(status="pending").count()
        unread   = Notification.query.filter_by(user_id=user_id, is_read=False).count()

        pending_prs = PurchaseRequest.query.filter_by(status="pending").count()
        pending_pos = PurchaseOrder.query.filter_by(status="draft").count()
        sent_pos    = PurchaseOrder.query.filter_by(status="sent").count()
        pending_grns = GoodsReceipt.query.count()
        month_start = today.replace(day=1)
        month_pos   = PurchaseOrder.query.filter(PurchaseOrder.created_at >= month_start).count()
        month_po_value = db.session.query(func.sum(PurchaseOrder.total_amount)).filter(
            PurchaseOrder.created_at >= month_start).scalar() or 0

        # Turnover rate: total out value (30d) / avg inventory value
        thirty_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        out_val_30d = db.session.query(func.sum(StockMovement.quantity * StockMovement.unit_price)).filter(
            StockMovement.type.in_(["out","damage"]),
            StockMovement.created_at >= thirty_ago).scalar() or 0
        turnover_rate = round(float(out_val_30d) / total_value, 2) if total_value > 0 else 0
        avg_storage_days = 30 / turnover_rate if turnover_rate > 0 else 0

        # Top items by stock value
        top_items = []
        for it in sorted(items, key=lambda x: x.get_total_stock() * x.unit_price, reverse=True)[:10]:
            s = it.get_total_stock()
            top_items.append({"id":it.id,"name":it.name,"code":it.code,"unit":it.unit,
                              "total_stock":s,"unit_price":it.unit_price,
                              "total_value":round(s * it.unit_price, 2)})

        # Top suppliers
        top_suppliers = db.session.query(
            Supplier.id, Supplier.name,
            func.count(PurchaseOrder.id).label("po_count"),
            func.sum(PurchaseOrder.total_amount).label("total_amount"),
        ).outerjoin(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id
        ).group_by(Supplier.id
        ).order_by(func.sum(PurchaseOrder.total_amount).desc().nullslast()
        ).limit(5).all()
        supplier_data = [{"id":s[0],"name":s[1],"po_count":s[2],"total_amount":float(s[3] or 0)} for s in top_suppliers]

        # Monthly procurement chart (last 6 months)
        po_chart = []
        month_names = ["ظٹظ†ط§ظٹط±","ظپط¨ط±ط§ظٹط±","ظ…ط§ط±ط³","ط£ط¨ط±ظٹظ„","ظ…ط§ظٹظˆ","ظٹظˆظ†ظٹظˆ","ظٹظˆظ„ظٹظˆ","ط£ط؛ط³ط·ط³","ط³ط¨طھظ…ط¨ط±","ط£ظƒطھظˆط¨ط±","ظ†ظˆظپظ…ط¨ط±","ط¯ظٹط³ظ…ط¨ط±"]
        for i in range(5, -1, -1):
            m = (today.replace(day=1) - datetime.timedelta(days=30*i)).replace(day=1)
            _, days_in_month = calendar.monthrange(m.year, m.month)
            m_end = m.replace(day=days_in_month)
            total = db.session.query(func.sum(PurchaseOrder.total_amount)).filter(
                PurchaseOrder.created_at >= m, PurchaseOrder.created_at <= m_end).scalar() or 0
            po_chart.append({"month": month_names[m.month-1], "value": round(float(total), 2)})

        # Consumption trend (last 6 months)
        cons_chart = []
        for i in range(5, -1, -1):
            m = (today.replace(day=1) - datetime.timedelta(days=30*i)).replace(day=1)
            _, days_in_month = calendar.monthrange(m.year, m.month)
            m_end = m.replace(day=days_in_month)
            total = db.session.query(func.sum(StockMovement.quantity)).filter(
                StockMovement.type.in_(["out","transfer","damage"]),
                StockMovement.created_at >= m, StockMovement.created_at <= m_end).scalar() or 0
            cons_chart.append({"month": month_names[m.month-1], "value": round(float(total), 2)})

        return {
            "kpis": {
                "total_items":       len(items),
                "total_value":       round(total_value, 2),
                "critical_count":    sum(1 for x in critical_items if x["status"]=="critical"),
                "warning_count":     sum(1 for x in critical_items if x["status"]=="warning"),
                "pending_transfers": pending,
                "today_in":          sum(m.quantity for m in today_movs if m.type=="in"),
                "today_out":         sum(m.quantity for m in today_movs if m.type=="out"),
                "total_movements":   StockMovement.query.count(),
                "pending_prs":       pending_prs,
                "pending_pos":       pending_pos,
                "sent_pos":          sent_pos,
                "month_pos":         month_pos,
                "month_po_value":    round(month_po_value, 2),
                "turnover_rate":     turnover_rate,
                "avg_storage_days":  round(avg_storage_days, 1),
            },
            "warehouses":           wh_stats,
            "critical_items":       critical_items,
            "recent_movements":     [m.to_dict() for m in recent],
            "chart_data":           chart,
            "po_chart":             po_chart,
            "cons_chart":           cons_chart,
            "top_items":            top_items,
            "top_suppliers":        supplier_data,
            "unread_notifications": unread,
        }


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  ITEM SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class ItemService:
    @staticmethod
    def get_list(search="", category_id=None, status="", page=1, per_page=50):
        q = Item.query.filter_by(is_active=True)
        if search:
            q = q.filter(
                (Item.name.contains(search)) |
                (Item.code.contains(search)) |
                (Item.barcode.contains(search))
            )
        if category_id:
            q = q.filter(Item.category_id == int(category_id))
        q = q.order_by(Item.name)
        result = paginate(q, page, per_page)
        items  = [i.to_dict() for i in result["items"]]
        if status == "critical":
            items = [i for i in items if i["status"] == "critical"]
        elif status == "warning":
            items = [i for i in items if i["status"] in ("critical","warning")]
        result["items"] = items
        return result

    @staticmethod
    def scan(code):
        return Item.query.filter(
            (Item.code == code) | (Item.barcode == code)
        ).first()

    @staticmethod
    def create(data, user_id):
        # Validate
        if Item.query.filter_by(code=data["code"]).first():
            return None, f"ط§ظ„ظƒظˆط¯ '{data['code']}' ظ…ط³طھط®ط¯ظ… ظ…ط³ط¨ظ‚ط§ظ‹"
        if data.get("barcode") and Item.query.filter_by(barcode=data["barcode"]).first():
            return None, "ط§ظ„ط¨ط§ط±ظƒظˆط¯ ظ…ط³طھط®ط¯ظ… ظ…ط³ط¨ظ‚ط§ظ‹"

        item = Item(
            code          = data["code"],
            barcode       = data.get("barcode"),
            name          = data["name"],
            category_id   = data.get("category_id"),
            unit          = data.get("unit", "ظ‚ط·ط¹ط©"),
            min_quantity  = float(data.get("min_quantity", 0)),
            reorder_point = float(data.get("reorder_point", 0)),
            unit_price    = float(data.get("unit_price", 0)),
            description   = data.get("description"),
        )
        db.session.add(item)
        db.session.flush()

        for wh in Warehouse.query.filter_by(is_active=True).all():
            qty = float((data.get("initial_stocks") or {}).get(str(wh.id), 0))
            db.session.add(Stock(item_id=item.id, warehouse_id=wh.id, quantity=qty))
            if qty > 0:
                db.session.add(StockMovement(
                    ref_number=gen_ref("IN"), type="in",
                    item_id=item.id, warehouse_id=wh.id,
                    quantity=qty, unit_price=item.unit_price,
                    user_id=user_id, notes="ط±طµظٹط¯ ط£ظˆظ„ظٹ",
                ))

        AuditService.log("create","item",item.id,f"ط¥ط¶ط§ظپط© طµظ†ظپ: {item.name}",new=data)
        db.session.commit()
        NotificationService.check_low_stock(item.id)
        return item, None

    @staticmethod
    def update(item_id, data, user_id):
        item = Item.query.get(item_id)
        if not item:
            return None, "ط§ظ„طµظ†ظپ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        old = item.to_dict(include_stock=False)
        for f in ["name","barcode","category_id","unit","min_quantity",
                  "reorder_point","unit_price","description","image_url","is_active"]:
            if f in data:
                setattr(item, f, data[f])
        AuditService.log("update","item",item_id,f"طھط­ط¯ظٹط«: {item.name}",old=old,new=data)
        db.session.commit()
        return item, None

    @staticmethod
    def delete(item_id):
        item = Item.query.get(item_id)
        if not item:
            return False, "ط§ظ„طµظ†ظپ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        item.is_active = False
        AuditService.log("delete","item",item_id,f"ط­ط°ظپ: {item.name}")
        db.session.commit()
        return True, None


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  MOVEMENT SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class MovementService:
    @staticmethod
    def get_list(filters, page=1, per_page=30):
        q = StockMovement.query
        if filters.get("type"):       q = q.filter(StockMovement.type == filters["type"])
        if filters.get("warehouse_id"):
            q = q.filter(StockMovement.warehouse_id == int(filters["warehouse_id"]))
        if filters.get("item_id"):    q = q.filter(StockMovement.item_id == int(filters["item_id"]))
        if filters.get("date_from"):  q = q.filter(StockMovement.created_at >= parse_date(filters["date_from"]))
        if filters.get("date_to"):
            q = q.filter(StockMovement.created_at <= parse_date(filters["date_to"]) + datetime.timedelta(days=1))
        if filters.get("search"):
            s = filters["search"]
            q = q.join(Item).filter((Item.name.contains(s)) | (StockMovement.ref_number.contains(s)))
        q = q.order_by(StockMovement.created_at.desc())
        return paginate(q, page, per_page)

    @staticmethod
    def create(data, user_id):
        item  = Item.query.get(data.get("item_id"))
        if not item:
            return None, "ط§ظ„طµظ†ظپ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"

        qty    = float(data["quantity"])
        wh_id  = int(data["warehouse_id"])
        mtype  = data["type"]

        if qty <= 0:
            return None, "ط§ظ„ظƒظ…ظٹط© ظٹط¬ط¨ ط£ظ† طھظƒظˆظ† ط£ظƒط¨ط± ظ…ظ† طµظپط±"

        # Check sufficient stock for outbound/damage
        dec = {"out","damage"}
        inc = {"in","return"}
        if mtype in dec:
            stock   = Stock.query.filter_by(item_id=item.id, warehouse_id=wh_id).first()
            current = stock.quantity if stock else 0
            if current < qty:
                return None, (f"ط§ظ„ظƒظ…ظٹط© ط§ظ„ظ…ط·ظ„ظˆط¨ط© ({qty} {item.unit}) "
                              f"طھطھط¬ط§ظˆط² ط§ظ„ط±طµظٹط¯ ط§ظ„ظ…طھط§ط­ ({current} {item.unit})")

        ref_prefix = {"in":"IN","out":"OUT","return":"RET","damage":"DAM"}.get(mtype,"MOV")
        mov = StockMovement(
            ref_number   = data.get("ref_number") or gen_ref(ref_prefix),
            type         = mtype,
            item_id      = item.id,
            warehouse_id = wh_id,
            quantity     = qty,
            unit_price   = float(data.get("unit_price") or item.unit_price or 0),
            supplier_id  = data.get("supplier_id"),
            user_id      = user_id,
            notes        = data.get("notes"),
            project      = data.get("project"),
            engineer_name = data.get("engineer_name"),
            lot_number    = data.get("lot_number") or None,
        )
        db.session.add(mov)

        # Update stock
        stock = Stock.get_or_create(item.id, wh_id)
        stock.quantity += qty if mtype in inc else -qty

        # FIFO layer tracking
        unit_cost = float(data.get("unit_price") or item.unit_price or 0)
        if mtype in inc and qty > 0:
            InventoryLayer.add_layer(item.id, wh_id, qty, unit_cost, ref_type="movement", ref_id=mov.id)
        elif mtype in dec and qty > 0:
            consumed_cost, consumed_qty = InventoryLayer.consume(item.id, wh_id, qty)
            diff = qty - consumed_qty
            if diff > 1e-6:
                InventoryLayer.add_layer(item.id, wh_id, -diff, unit_cost, ref_type="movement_adj", ref_id=mov.id)

        lbl = StockMovement.TYPE_LABELS.get(mtype, mtype)

        AuditService.log("create","movement",mov.id,
                         f"{lbl}: {item.name} {qty} {item.unit}")
        db.session.commit()
        NotificationService.check_low_stock(item.id)
        return mov, None

    @staticmethod
    def adjust(data, user_id):
        item  = Item.query.get(data.get("item_id"))
        wh_id = int(data["warehouse_id"])
        if not item: return None, "ط§ظ„طµظ†ظپ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        wh = Warehouse.query.get(wh_id)
        if not wh: return None, "ط§ظ„ظ…ط®ط²ظ† ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        new_qty = float(data["new_quantity"])
        if new_qty < 0: return None, "ط§ظ„ظƒظ…ظٹط© ظ„ط§ ظٹظ…ظƒظ† ط£ظ† طھظƒظˆظ† ط³ط§ظ„ط¨ط©"
        stock = Stock.get_or_create(item.id, wh_id)
        current = stock.quantity
        diff = new_qty - current
        if diff == 0: return None, "ط§ظ„ظƒظ…ظٹط© ط§ظ„ط¬ط¯ظٹط¯ط© طھط³ط§ظˆظٹ ط§ظ„ظƒظ…ظٹط© ط§ظ„ط­ط§ظ„ظٹط© â€” ظ„ط§ ظٹظˆط¬ط¯ طھط؛ظٹظٹط±"
        mtype = "in" if diff > 0 else "out"
        mov = StockMovement(
            ref_number = gen_ref("ADJ"),
            type       = "adjustment",
            item_id    = item.id,
            warehouse_id = wh_id,
            quantity   = abs(diff),
            unit_price = float(data.get("unit_price") or item.unit_price or 0),
            user_id    = user_id,
            notes      = data.get("notes","") or "",
            project    = data.get("reason","other"),
        )
        db.session.add(mov)
        stock.quantity = new_qty
        AuditService.log("create","movement",mov.id,
                         f"طھط³ظˆظٹط©: {item.name} {current} â†’ {new_qty} {item.unit}")
        db.session.commit()
        NotificationService.check_low_stock(item.id)
        return mov, None


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  TRANSFER SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class TransferService:
    @staticmethod
    def get_list(status=None):
        q = Transfer.query
        if status:
            q = q.filter(Transfer.status == status)
        return q.order_by(Transfer.created_at.desc()).all()

    @staticmethod
    def create(data, user_id):
        if data.get("from_warehouse_id") == data.get("to_warehouse_id"):
            return None, "ظ…ط®ط²ظ† ط§ظ„ظ…طµط¯ط± ظˆط§ظ„ظ‡ط¯ظپ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† ظٹظƒظˆظ†ط§ ظ…طھظ…ط§ط«ظ„ظٹظ†"

        item = Item.query.get(data.get("item_id"))
        if not item:
            return None, "ط§ظ„طµظ†ظپ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"

        qty = float(data["quantity"])
        stock = Stock.query.filter_by(
            item_id=item.id, warehouse_id=data["from_warehouse_id"]
        ).first()
        avail = stock.quantity if stock else 0
        if avail < qty:
            return None, f"ط§ظ„ط±طµظٹط¯ ط؛ظٹط± ظƒط§ظپظچ â€” ط§ظ„ظ…طھط§ط­: {avail} {item.unit}"

        tr = Transfer(
            ref_number        = gen_ref("TR"),
            item_id           = item.id,
            from_warehouse_id = data["from_warehouse_id"],
            to_warehouse_id   = data["to_warehouse_id"],
            quantity          = qty,
            reason            = data.get("reason"),
            requested_by      = user_id,
            status            = "pending",
        )
        # auto-assign active approval chain for transfers
        chain = ApprovalChain.query.filter_by(target_type="transfer", is_active=True).first()
        if chain:
            tr.approval_chain_id = chain.id
            tr.current_step = 0
        db.session.add(tr)
        db.session.flush()

        NotificationService.push(
            "transfer_request",
            f"ًں”„ ط·ظ„ط¨ طھط­ظˆظٹظ„: {item.name}",
            f"ط·ظ„ط¨ {qty} {item.unit} ظ…ظ† {tr.from_wh.name} ط¥ظ„ظ‰ {tr.to_wh.name}",
            ref_type="transfer", ref_id=tr.id,
        )
        AuditService.log("create","transfer",tr.id,
                         f"ط·ظ„ط¨ طھط­ظˆظٹظ„: {item.name} {qty}")
        db.session.commit()
        return tr, None

    @staticmethod
    def approve(transfer_id, approver_id):
        tr = Transfer.query.get(transfer_id)
        if not tr:
            return None, "ط§ظ„ط·ظ„ط¨ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        if tr.status != "pending":
            return None, "طھظ…طھ ظ…ط¹ط§ظ„ط¬ط© ظ‡ط°ط§ ط§ظ„ط·ظ„ط¨ ظ…ط³ط¨ظ‚ط§ظ‹"

        sf = Stock.query.filter_by(item_id=tr.item_id,
                                    warehouse_id=tr.from_warehouse_id).first()
        if not sf or sf.quantity < tr.quantity:
            return None, "ط§ظ„ط±طµظٹط¯ ط؛ظٹط± ظƒط§ظپظچ ظ„طھظ†ظپظٹط° ط§ظ„طھط­ظˆظٹظ„"

        sf.quantity -= tr.quantity
        st = Stock.get_or_create(tr.item_id, tr.to_warehouse_id)
        st.quantity += tr.quantity

        mov = StockMovement(
            ref_number          = gen_ref("TR"),
            type                = "transfer",
            item_id             = tr.item_id,
            warehouse_id        = tr.from_warehouse_id,
            target_warehouse_id = tr.to_warehouse_id,
            quantity            = tr.quantity,
            user_id             = approver_id,
            notes               = f"طھط­ظˆظٹظ„ ظ…ط¹طھظ…ط¯ â€” {tr.ref_number}",
        )
        db.session.add(mov)
        db.session.flush()

        tr.status      = "executed"
        tr.approved_by = approver_id
        tr.approved_at = datetime.datetime.utcnow()
        tr.movement_id = mov.id

        AuditService.log("approve","transfer",transfer_id,f"ط§ط¹طھظ…ط§ط¯: {tr.ref_number}")
        db.session.commit()
        NotificationService.check_low_stock(tr.item_id)
        return tr, None

    @staticmethod
    def reject(transfer_id, approver_id, reason=""):
        tr = Transfer.query.get(transfer_id)
        if not tr:
            return None, "ط§ظ„ط·ظ„ط¨ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        if tr.status != "pending":
            return None, "طھظ…طھ ظ…ط¹ط§ظ„ط¬ط© ظ‡ط°ط§ ط§ظ„ط·ظ„ط¨ ظ…ط³ط¨ظ‚ط§ظ‹"

        tr.status        = "rejected"
        tr.approved_by   = approver_id
        tr.approved_at   = datetime.datetime.utcnow()
        tr.reject_reason = reason

        AuditService.log("reject","transfer",transfer_id,f"ط±ظپط¶: {tr.ref_number}")
        db.session.commit()
        return tr, None


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  INVENTORY COUNT SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class CountService:
    @staticmethod
    def get_list():
        return InventoryCount.query.order_by(InventoryCount.started_at.desc()).all()

    @staticmethod
    def create(data, user_id):
        wh_id = data.get("warehouse_id")
        if not wh_id:
            return None, "ط§ظ„ظ…ط®ط²ظ† ظ…ط·ظ„ظˆط¨"
        if InventoryCount.query.filter_by(warehouse_id=wh_id, status="active").first():
            return None, "ظٹظˆط¬ط¯ ط¬ظ„ط³ط© ط¬ط±ط¯ ظ†ط´ط·ط© ظ„ظ‡ط°ط§ ط§ظ„ظ…ط®ط²ظ†"

        count = InventoryCount(
            ref_number    = gen_ref("CNT"),
            warehouse_id  = wh_id,
            supervisor_id = data.get("supervisor_id") or user_id,
            notes         = data.get("notes"),
        )
        db.session.add(count)
        db.session.flush()

        for s in Stock.query.filter_by(warehouse_id=wh_id).all():
            if s.item and s.item.is_active:
                db.session.add(InventoryCountLine(
                    count_id=count.id, item_id=s.item_id,
                    system_quantity=s.quantity,
                ))

        AuditService.log("create","count",count.id,f"ط¨ط¯ط، ط¬ط±ط¯: {count.ref_number}")
        db.session.commit()
        return count, None

    @staticmethod
    def update_line(count_id, line_id, actual_qty, notes=""):
        line = InventoryCountLine.query.get(line_id)
        if not line or line.count_id != count_id:
            return None, "ط§ظ„ط³ط·ط± ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        line.actual_quantity = float(actual_qty)
        line.notes           = notes
        db.session.commit()
        return line, None

    @staticmethod
    def complete(count_id, user_id):
        count = InventoryCount.query.get(count_id)
        if not count:
            return None, "ط§ظ„ط¬ظ„ط³ط© ط؛ظٹط± ظ…ظˆط¬ظˆط¯ط©"
        if count.status != "active":
            return None, "ط§ظ„ط¬ظ„ط³ط© ط؛ظٹط± ظ†ط´ط·ط©"

        diffs = 0
        for line in count.lines:
            if line.actual_quantity is not None and line.actual_quantity != line.system_quantity:
                stock = Stock.get_or_create(line.item_id, count.warehouse_id)
                diff  = line.actual_quantity - line.system_quantity
                stock.quantity = line.actual_quantity
                db.session.add(StockMovement(
                    ref_number   = gen_ref("ADJ"),
                    type         = "in" if diff > 0 else "out",
                    item_id      = line.item_id,
                    warehouse_id = count.warehouse_id,
                    quantity     = abs(diff),
                    user_id      = user_id,
                    notes        = f"طھط³ظˆظٹط© ط¬ط±ط¯ â€” {count.ref_number}",
                ))
                diffs += 1

        count.status       = "completed"
        count.completed_at = datetime.datetime.utcnow()

        if diffs > 0:
            NotificationService.push(
                "count_diff",
                f"âڑ–ï¸ڈ ظپط±ظˆظ‚ط§طھ ط¬ط±ط¯: {count.warehouse.name}",
                f"{diffs} ظپط±ظˆظ‚ط§طھ ظپظٹ {count.ref_number}",
                ref_type="count", ref_id=count.id,
            )

        AuditService.log("complete","count",count_id,
                         f"ط¥ط؛ظ„ط§ظ‚ ط¬ط±ط¯: {count.ref_number} â€” {diffs} ظپط±ظˆظ‚ط§طھ")
        db.session.commit()
        return {"differences": diffs, "count": count}, None


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  SUPPLIER SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class SupplierService:
    @staticmethod
    def get_list(search=""):
        q = Supplier.query.filter_by(is_active=True)
        if search:
            q = q.filter(
                (Supplier.name.contains(search)) | (Supplier.category.contains(search))
            )
        return q.order_by(Supplier.name).all()

    @staticmethod
    def create(data):
        if not data.get("name"):
            return None, "ط§ط³ظ… ط§ظ„ظ…ظˆط±ط¯ ظ…ط·ظ„ظˆط¨"
        s = Supplier(
            code          = data.get("code") or gen_ref("SUP"),
            name          = data["name"],
            category      = data.get("category"),
            phone         = data.get("phone"),
            email         = data.get("email"),
            address       = data.get("address"),
            tax_number    = data.get("tax_number"),
            payment_terms = data.get("payment_terms", "ظ†ظ‚ط¯ط§ظ‹"),
            rating        = data.get("rating", 3),
            notes         = data.get("notes"),
        )
        db.session.add(s)
        AuditService.log("create","supplier",None,f"ظ…ظˆط±ط¯: {s.name}")
        db.session.commit()
        return s, None

    @staticmethod
    def update(supplier_id, data):
        s = Supplier.query.get(supplier_id)
        if not s:
            return None, "ط§ظ„ظ…ظˆط±ط¯ ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        for f in ["name","category","phone","email","address",
                  "tax_number","payment_terms","rating","is_active","notes"]:
            if f in data:
                setattr(s, f, data[f])
        AuditService.log("update","supplier",supplier_id,f"طھط­ط¯ظٹط«: {s.name}")
        db.session.commit()
        return s, None


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  USER SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class UserService:
    @staticmethod
    def get_list():
        return User.query.filter_by(is_active=True).all()

    @staticmethod
    def create(data):
        errs = {}
        if not data.get("name"):     errs["name"]     = "ط§ظ„ط§ط³ظ… ظ…ط·ظ„ظˆط¨"
        if not data.get("username"): errs["username"]  = "ط§ط³ظ… ط§ظ„ظ…ط³طھط®ط¯ظ… ظ…ط·ظ„ظˆط¨"
        if not data.get("password"): errs["password"]  = "ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظ…ط·ظ„ظˆط¨ط©"
        elif len(data["password"]) < 6:
            errs["password"] = "ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظٹط¬ط¨ ط£ظ† طھظƒظˆظ† 6 ط£ط­ط±ظپ ط¹ظ„ظ‰ ط§ظ„ط£ظ‚ظ„"
        if errs:
            return None, errs
        if User.query.filter_by(username=data["username"]).first():
            return None, {"username": "ط§ط³ظ… ط§ظ„ظ…ط³طھط®ط¯ظ… ظ…ط³طھط®ط¯ظ… ظ…ط³ط¨ظ‚ط§ظ‹"}

        u = User(
            name         = data["name"],
            username     = data["username"],
            email        = data.get("email"),
            role         = data.get("role", "keeper"),
            warehouse_id = data.get("warehouse_id"),
        )
        u.set_password(data["password"])
        db.session.add(u)
        AuditService.log("create","user",None,f"ظ…ط³طھط®ط¯ظ…: {u.name}")
        db.session.commit()
        return u, None

    @staticmethod
    def update(user_id, data, current_user_id):
        if user_id == current_user_id and data.get("is_active") is False:
            return None, "ظ„ط§ ظٹظ…ظƒظ†ظƒ طھط¹ط·ظٹظ„ ط­ط³ط§ط¨ظƒ ط§ظ„ط®ط§طµ"
        u = User.query.get(user_id)
        if not u:
            return None, "ط§ظ„ظ…ط³طھط®ط¯ظ… ط؛ظٹط± ظ…ظˆط¬ظˆط¯"
        for f in ["name","email","role","warehouse_id","is_active"]:
            if f in data:
                setattr(u, f, data[f])
        if data.get("password"):
            if len(data["password"]) < 6:
                return None, "ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظ‚طµظٹط±ط© ط¬ط¯ط§ظ‹"
            u.set_password(data["password"])
        AuditService.log("update","user",user_id,f"طھط­ط¯ظٹط«: {u.name}")
        db.session.commit()
        return u, None


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  PURCHASE ORDER SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
# procurement logic moved to routes.py

# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  STOCK INQUIRY SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class StockInquiryService:
    @staticmethod
    def search(query=""):
        q = Item.query.filter_by(is_active=True)
        if query:
            q = q.filter(Item.name.contains(query) | Item.code.contains(query) | Item.barcode.contains(query))
        items = q.order_by(Item.name).all()
        whs = Warehouse.query.filter_by(is_active=True).all()
        result = []
        for item in items:
            stocks = {s.warehouse_id: s.quantity for s in item.stocks}
            total = sum(stocks.values())
            wh_data = {}
            for wh in whs:
                wh_data[f"wh_{wh.id}"] = stocks.get(wh.id, 0)
                wh_data[f"wh_{wh.id}_name"] = wh.name
            result.append({
                "id": item.id, "code": item.code, "barcode": item.barcode,
                "name": item.name, "category": item.category.name if item.category else "",
                "unit": item.unit, "unit_price": item.unit_price,
                "min_quantity": item.min_quantity, "reorder_point": item.reorder_point,
                "total_stock": total, "status": item.get_status(),
                "status_label": item.get_status_label(),
                **wh_data,
            })
        return {"items": result, "warehouses": [w.to_dict() for w in whs]}


# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
#  REPORT SERVICE
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
class ReportService:
    @staticmethod
    def balance():
        whs   = Warehouse.query.filter_by(is_active=True).all()
        items = Item.query.filter_by(is_active=True).all()
        rows  = []
        for item in items:
            stocks = {s.warehouse_id: s.quantity for s in item.stocks}
            total  = sum(stocks.values())
            row    = {
                "code":      item.code,
                "name":      item.name,
                "category":  item.category.name if item.category else "",
                "unit":      item.unit,
                "unit_price":item.unit_price,
                "min_quantity": item.min_quantity,
                "total":     total,
                "total_value": round(total * item.unit_price, 2),
                "status":    item.get_status(),
                "status_label": item.get_status_label(),
            }
            for wh in whs:
                row[f"wh_{wh.id}"]      = stocks.get(wh.id, 0)
                row[f"wh_{wh.id}_name"] = wh.name
            rows.append(row)
        return {"rows": rows, "warehouses": [w.to_dict() for w in whs]}

    @staticmethod
    def daily(date_from, date_to=None):
        import datetime as dt
        try:
            d = dt.datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            return None, "طھط§ط±ظٹط® ط؛ظٹط± طµط­ظٹط­"
        q = StockMovement.query
        if date_to:
            try:
                d2 = dt.datetime.strptime(date_to, "%Y-%m-%d").date() + dt.timedelta(days=1)
            except ValueError:
                return None, "طھط§ط±ظٹط® ط§ظ„ظ†ظ‡ط§ظٹط© ط؛ظٹط± طµط­ظٹط­"
            q = q.filter(StockMovement.created_at >= d, StockMovement.created_at < d2)
        else:
            q = q.filter(func.date(StockMovement.created_at) == d)
        movs = q.order_by(StockMovement.created_at.desc()).all()
        return {
            "date_from": date_from,
            "date_to":   date_to or date_from,
            "movements": [m.to_dict() for m in movs],
            "summary": {
                "total_in":       sum(m.quantity for m in movs if m.type=="in"),
                "total_out":      sum(m.quantity for m in movs if m.type=="out"),
                "total_return":   sum(m.quantity for m in movs if m.type=="return"),
                "total_damage":   sum(m.quantity for m in movs if m.type=="damage"),
                "total_transfer": sum(m.quantity for m in movs if m.type=="transfer"),
                "count":          len(movs),
            },
        }, None

    @staticmethod
    def transfers(date_from=None, date_to=None):
        import datetime as dt
        q = Transfer.query
        if date_from:
            try:
                d = dt.datetime.strptime(date_from, "%Y-%m-%d").date()
                q = q.filter(func.date(Transfer.created_at) >= d)
            except ValueError:
                pass
        if date_to:
            try:
                d2 = dt.datetime.strptime(date_to, "%Y-%m-%d").date()
                q = q.filter(func.date(Transfer.created_at) <= d2)
            except ValueError:
                pass
        ts = q.order_by(Transfer.created_at.desc()).all()
        pending  = sum(1 for t in ts if t.status=="pending")
        executed = sum(1 for t in ts if t.status=="executed")
        rejected = sum(1 for t in ts if t.status=="rejected")
        return {"transfers":[t.to_dict() for t in ts],
                "summary":{"total":len(ts),"pending":pending,
                           "executed":executed,"rejected":rejected}}

    @staticmethod
    def budget():
        projects = Project.query.order_by(Project.name).all()
        result = []
        for p in projects:
            out_v = db.session.query(func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_price), 0))\
                .filter(StockMovement.project == p.name, StockMovement.type == 'out').scalar()
            ret_v = db.session.query(func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_price), 0))\
                .filter(StockMovement.project == p.name, StockMovement.type == 'return').scalar()
            dam_v = db.session.query(func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_price), 0))\
                .filter(StockMovement.project == p.name, StockMovement.type == 'damage').scalar()
            spent = round(float(out_v) + float(dam_v) - float(ret_v), 2)
            result.append({
                "id":p.id,"name":p.name,"code":p.code or "",
                "client":p.client or "","status":p.status,
                "status_label":"ظ†ط´ط·" if p.status=="active" else "ظ…طھظˆظ‚ظپ",
                "budget":p.budget or 0,
                "spent":spent,
                "remaining":round(p.budget - spent,2) if p.budget else -spent,
                "usage_pct":round(spent/(p.budget or 0)*100,1) if p.budget and p.budget>0 else 0,
            })
        total_budget = sum(r["budget"] for r in result)
        total_spent  = sum(r["spent"] for r in result)
        return {"projects":result,
                "summary":{"total":len(result),"active":sum(1 for r in result if r["status"]=="active"),
                           "total_budget":round(total_budget,2),"total_spent":round(total_spent,2),
                           "total_remaining":round(total_budget-total_spent,2)}}

    @staticmethod
    def export_excel(report_type):
        import io
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb  = openpyxl.Workbook()
        ws  = wb.active

        hf  = Font(bold=True, color="FFFFFF", size=11)
        hfl = PatternFill(start_color="1B4F72", end_color="1B4F72", fill_type="solid")
        af  = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
        ra  = Alignment(horizontal="right", vertical="center")
        ca  = Alignment(horizontal="center", vertical="center")
        th  = Side(style="thin", color="BDC3C7")
        bdr = Border(left=th, right=th, top=th, bottom=th)

        def style_header(row, cols):
            for c in range(1, cols+1):
                cell = ws.cell(row=row, column=c)
                cell.font=hf; cell.fill=hfl; cell.alignment=ca; cell.border=bdr

        def style_row(row, cols, alt=False):
            for c in range(1, cols+1):
                cell = ws.cell(row=row, column=c)
                if alt: cell.fill=af
                cell.alignment=ra; cell.border=bdr

        ws.sheet_view.rightToLeft = True

        if report_type == "balance":
            ws.title = "ط±طµظٹط¯ ط§ظ„ظ…ط®ط§ط²ظ†"
            whs = Warehouse.query.filter_by(is_active=True).all()
            ws.merge_cells(f"A1:{get_column_letter(5+len(whs))}1")
            ws["A1"] = f"طھظ‚ط±ظٹط± ط±طµظٹط¯ ط§ظ„ظ…ط®ط§ط²ظ† â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28

            headers = ["ط§ظ„ظƒظˆط¯","ط§ظ„طµظ†ظپ","ط§ظ„ظپط¦ط©","ط§ظ„ظˆط­ط¯ط©"] + \
                      [wh.name for wh in whs] + ["ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹ","ط§ظ„ظ‚ظٹظ…ط© (ط±.ط³)","ط§ظ„ط­ط§ظ„ط©"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))

            for ri, item in enumerate(Item.query.filter_by(is_active=True).all(), 3):
                stocks = {s.warehouse_id: s.quantity for s in item.stocks}
                total  = sum(stocks.values())
                row_d  = [item.code, item.name,
                          item.category.name if item.category else "",
                          item.unit] + [stocks.get(wh.id,0) for wh in whs] + \
                         [total, round(total*item.unit_price,2), item.get_status_label()]
                for col, val in enumerate(row_d, 1):
                    ws.cell(row=ri, column=col)
                    wh_start_col = 5
                    wh_end_col = 4 + len(whs)
                    total_col = wh_end_col + 1
                    if col == total_col:
                        ws.cell(row=ri, column=col).value = \
                            f"=SUM({get_column_letter(wh_start_col)}{ri}:{get_column_letter(wh_end_col)}{ri})"
                    elif col == total_col + 1:
                        ws.cell(row=ri, column=col).value = \
                            f"={get_column_letter(total_col)}{ri}*{item.unit_price}"
                    else:
                        ws.cell(row=ri, column=col).value = val
                style_row(ri, len(headers), alt=ri%2==0)
                sc = ws.cell(row=ri, column=len(headers))
                if item.get_status()=="critical":
                    sc.fill=PatternFill(start_color="FADBD8",end_color="FADBD8",fill_type="solid")
                    sc.font=Font(color="C0392B",bold=True)
                elif item.get_status()=="warning":
                    sc.fill=PatternFill(start_color="FDEBD0",end_color="FDEBD0",fill_type="solid")
                    sc.font=Font(color="CA6F1E",bold=True)

        elif report_type == "movements":
            ws.title = "ط³ط¬ظ„ ط§ظ„ط­ط±ظƒط§طھ"
            headers = ["#","ط§ظ„طھط§ط±ظٹط®","ط§ظ„ظˆظ‚طھ","ط§ظ„طµظ†ظپ","ط§ظ„ظ†ظˆط¹","ط§ظ„ظƒظ…ظٹط©",
                       "ط§ظ„ظˆط­ط¯ط©","ط§ظ„ظ…ط®ط²ظ†","ط§ظ„ظ…ظ†ظپط°","ط§ظ„ظ…ط±ط¬ط¹","ط§ظ„ظ…ط´ط±ظˆط¹","ط§ظ„ظ…ظ‡ظ†ط¯ط³","ظ…ظ„ط§ط­ط¸ط§طھ"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=h)
            style_header(1, len(headers))
            tmap = {"in":"ظˆط§ط±ط¯","out":"طµط±ظپ","transfer":"طھط­ظˆظٹظ„","adjustment":"طھط³ظˆظٹط©",
                    "return":"ظ…ط±طھط¬ط¹","damage":"ظ‡ط§ظ„ظƒ"}
            for ri, m in enumerate(
                StockMovement.query.order_by(StockMovement.created_at.desc()).limit(1000).all(), 2
            ):
                rd = [m.id, m.created_at.strftime("%d/%m/%Y"), m.created_at.strftime("%H:%M"),
                      m.item.name if m.item else "",
                      tmap.get(m.type,""), m.quantity,
                      m.item.unit if m.item else "",
                      m.warehouse.name if m.warehouse else "",
                      m.user.name if m.user else "",
                      m.ref_number,
                      m.project or "",
                      m.engineer_name or "",
                      m.notes or ""]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        elif report_type == "transfers":
            ws.title = "ط§ظ„طھط­ظˆظٹظ„ط§طھ"
            headers = ["#","ط±ظ‚ظ… ط§ظ„ظ…ط±ط¬ط¹","ط§ظ„طµظ†ظپ","ط§ظ„ظƒظ…ظٹط©","ط§ظ„ظˆط­ط¯ط©","ظ…ظ† ظ…ط®ط²ظ†","ط¥ظ„ظ‰ ظ…ط®ط²ظ†","ط§ظ„ط·ط§ظ„ط¨","ط§ظ„طھط§ط±ظٹط®","ط§ظ„ط³ط¨ط¨","ط§ظ„ط­ط§ظ„ط©"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=h)
            style_header(1, len(headers))
            for ri, t in enumerate(
                Transfer.query.order_by(Transfer.created_at.desc()).all(), 2
            ):
                rd = [t.id, t.ref_number or "",
                      t.item.name if t.item else "", t.quantity,
                      t.item.unit if t.item else "",
                      t.from_wh.name if t.from_wh else "",
                      t.to_wh.name if t.to_wh else "",
                      t.requester.name if t.requester else "",
                      t.created_at.strftime("%d/%m/%Y") if t.created_at else "",
                      t.reason or "",
                      t.STATUS_LABELS.get(t.status,t.status)]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        elif report_type == "diffs":
            ws.title = "ظپط±ظˆظ‚ط§طھ ط§ظ„ط¬ط±ط¯"
            headers = ["#","ط§ظ„طµظ†ظپ","ظƒظˆط¯ ط§ظ„طµظ†ظپ","ط§ظ„ظ…ط®ط²ظ†","ظƒظ…ظٹط© ط§ظ„ظ†ط¸ط§ظ…","ط§ظ„ظƒظ…ظٹط© ط§ظ„ظپط¹ظ„ظٹط©","ط§ظ„ظپط±ظ‚","ظ…ظ„ط§ط­ط¸ط§طھ","طھط§ط±ظٹط® ط§ظ„ط¬ط±ط¯"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=h)
            style_header(1, len(headers))
            diffs = (db.session.query(InventoryCountLine)
                     .join(InventoryCount)
                     .filter(
                         InventoryCountLine.actual_quantity.isnot(None),
                         InventoryCountLine.actual_quantity != InventoryCountLine.system_quantity,
                         InventoryCount.status == "completed"
                     )
                     .order_by(InventoryCount.completed_at.desc())
                     .all())
            for ri, l in enumerate(diffs, 2):
                rd = [l.id,
                      l.item.name if l.item else "",
                      l.item.code if l.item else "",
                      l.count.warehouse.name if l.count and l.count.warehouse else "",
                      l.system_quantity, l.actual_quantity,
                      l.difference, l.notes or "",
                      l.count.completed_at.strftime("%d/%m/%Y") if l.count and l.count.completed_at else ""]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        elif report_type == "budget":
            ws.title = "ط§ظ„ظ…ظٹط²ط§ظ†ظٹط©"
            ws.merge_cells("A1:H1")
            ws["A1"] = f"طھظ‚ط±ظٹط± ظ…ظٹط²ط§ظ†ظٹط© ط§ظ„ظ…ط´ط§ط±ظٹط¹ â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["ط§ظ„ظ…ط´ط±ظˆط¹","ط§ظ„ظƒظˆط¯","ط§ظ„ط¹ظ…ظٹظ„","ط§ظ„ظ…ظٹط²ط§ظ†ظٹط©","ط§ظ„ظ…ظ†طµط±ظپ","ط§ظ„ظ…طھط¨ظ‚ظٹ","ط§ظ„ط§ط³طھط®ط¯ط§ظ… %","ط§ظ„ط­ط§ظ„ط©"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            data = ReportService.budget()
            for ri, p in enumerate(data["projects"], 3):
                rd = [p["name"],p["code"],p["client"],p["budget"],p["spent"],p["remaining"],
                      p["usage_pct"],p["status_label"]]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                    if col == 4: ws.cell(row=ri,column=col).number_format = '#,##0.00'
                    if col in (5,6): ws.cell(row=ri,column=col).number_format = '#,##0.00'
                style_row(ri, len(headers), alt=ri%2==0)
            # summary row
            sr = ri + 1
            ws.cell(row=sr, column=1, value="ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹ").font = Font(bold=True)
            ws.cell(row=sr, column=4, value=data["summary"]["total_budget"]).number_format = '#,##0.00'
            ws.cell(row=sr, column=5, value=data["summary"]["total_spent"]).number_format = '#,##0.00'
            ws.cell(row=sr, column=6, value=data["summary"]["total_remaining"]).number_format = '#,##0.00'
            for c in range(1, len(headers)+1):
                ws.cell(row=sr, column=c).border = bdr
                ws.cell(row=sr, column=c).font = Font(bold=True)

        elif report_type == "consumption":
            ws.title = "ط§ظ„ط§ط³طھظ‡ظ„ط§ظƒ"
            ws.merge_cells("A1:F1")
            ws["A1"] = f"طھظ‚ط±ظٹط± ط§ظ„ط§ط³طھظ‡ظ„ط§ظƒ â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["ط§ظ„طµظ†ظپ","ط§ظ„ظƒظˆط¯","ط§ظ„ظƒظ…ظٹط© ط§ظ„ظ…ط³طھظ‡ظ„ظƒط©","ط§ظ„ظ‚ظٹظ…ط©","ط¹ط¯ط¯ ط§ظ„ط­ط±ظƒط§طھ","ظ…طھظˆط³ط· ط§ظ„ظٹظˆظ…"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            days = 30
            since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            rows = db.session.query(
                StockMovement.item_id, Item.name, Item.code,
                func.sum(StockMovement.quantity).label("total_qty"),
                func.sum(StockMovement.quantity * StockMovement.unit_price).label("total_val"),
                func.count(StockMovement.id).label("mov_count")
            ).join(Item, StockMovement.item_id == Item.id
            ).filter(StockMovement.type.in_(["out","transfer","damage"]),
                     StockMovement.created_at >= since
            ).group_by(StockMovement.item_id
            ).order_by(func.sum(StockMovement.quantity).desc()
            ).limit(50).all()
            for ri, r in enumerate(rows, 3):
                rd = [r[1], r[2], int(r[3]), round(float(r[4] or 0),2), r[5], round(float(r[3])/max(days,1),2)]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        elif report_type == "fastslow":
            ws.title = "ط³ط±ظٹط¹/ط¨ط·ظٹط،"
            ws.merge_cells("A1:D1")
            ws["A1"] = f"ط§ظ„ط£طµظ†ط§ظپ ط³ط±ظٹط¹ط©/ط¨ط·ظٹط¦ط© ط§ظ„ط­ط±ظƒط© â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["ط§ظ„ظ†ظˆط¹","ط§ظ„طµظ†ظپ","ط§ظ„ظƒظ…ظٹط© ط§ظ„ظ…ط³طھظ‡ظ„ظƒط©","ط§ظ„ظ…ط®ط²ظˆظ† ط§ظ„ط­ط§ظ„ظٹ"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            days = 90
            since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            out_q = db.session.query(StockMovement.item_id, func.sum(StockMovement.quantity).label("qty")).filter(
                StockMovement.type.in_(["out","transfer","damage"]), StockMovement.created_at >= since
            ).group_by(StockMovement.item_id).subquery()
            items = db.session.query(Item.id, Item.name, Item.code,
                                     func.coalesce(out_q.c.qty, 0).label("consumed"),
                                     func.coalesce(func.sum(Stock.quantity), 0).label("current_stock")
            ).outerjoin(out_q, Item.id == out_q.c.item_id
            ).outerjoin(Stock, Stock.item_id == Item.id
            ).group_by(Item.id).all()
            fast = sorted(items, key=lambda x: float(x.consumed or 0), reverse=True)[:10]
            slow = sorted([it for it in items if float(it.consumed or 0) <= 0], key=lambda x: float(x.current_stock or 0), reverse=True)[:10]
            ri = 3
            for i in fast:
                rd = ["ط³ط±ظٹط¹ ط§ظ„ط­ط±ظƒط©", i[1], int(i[3]), int(i[4])]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0); ri += 1
            for i in slow:
                rd = ["ط¨ط·ظٹط، ط§ظ„ط­ط±ظƒط©", i[1], int(i[3]), int(i[4])]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0); ri += 1

        elif report_type == "supplier_perf":
            ws.title = "ط£ط¯ط§ط، ط§ظ„ظ…ظˆط±ط¯ظٹظ†"
            ws.merge_cells("A1:G1")
            ws["A1"] = f"طھظ‚ط±ظٹط± ط£ط¯ط§ط، ط§ظ„ظ…ظˆط±ط¯ظٹظ† â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["ط§ظ„ظ…ظˆط±ط¯","ط£ظˆط§ظ…ط± ط§ظ„ط´ط±ط§ط،","ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹ","ط§ظ„ط¥ط³طھظ„ط§ظ…ط§طھ","ط¯ظ‚ط© ط§ظ„طھط³ظ„ظٹظ…","ط§ظ„ط¬ظˆط¯ط©","ط§ظ„ظ…ط¹ط¯ظ„"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            sp_rows = db.session.query(
                Supplier.id, Supplier.name,
                func.count(PurchaseOrder.id).label("po_count"),
                func.sum(PurchaseOrder.total_amount).label("total_amount"),
                func.count(GoodsReceipt.id).label("grn_count"),
            ).outerjoin(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id
            ).outerjoin(GoodsReceipt, GoodsReceipt.po_id == PurchaseOrder.id
            ).group_by(Supplier.id).all()
            sp_evals = SupplierEvaluation.query.with_entities(
                SupplierEvaluation.supplier_id,
                func.avg(SupplierEvaluation.quality).label("avg_quality"),
                func.avg(SupplierEvaluation.delivery).label("avg_delivery"),
            ).group_by(SupplierEvaluation.supplier_id).all()
            sp_emap = {e[0]:{"quality":round(float(e[1] or 0),1),"delivery":round(float(e[2] or 0),1)} for e in sp_evals}
            for ri, r in enumerate(sp_rows, 3):
                ev = sp_emap.get(r[0],{})
                avg = (ev.get("delivery",0) + ev.get("quality",0))/2
                rd = [r[1] or "", r[2] or 0, round(float(r[3] or 0),2), r[4] or 0,
                      ev.get("delivery",0), ev.get("quality",0), round(avg,1)]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        elif report_type == "valuation":
            ws.title = "طھظ‚ظٹظٹظ… ط§ظ„ظ…ط®ط²ظˆظ†"
            ws.merge_cells("A1:F1")
            ws["A1"] = f"طھظ‚ظٹظٹظ… ط§ظ„ظ…ط®ط²ظˆظ† (FIFO) â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["ط§ظ„طµظ†ظپ","ط§ظ„ظƒظˆط¯","ط§ظ„ظƒظ…ظٹط© ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹط©","ظ…طھظˆط³ط· ط§ظ„طھظƒظ„ظپط©","ط§ظ„ظ‚ظٹظ…ط© ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹط©","ط¹ط¯ط¯ ط§ظ„ط·ط¨ظ‚ط§طھ"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            ri = 3
            for it in Item.query.filter_by(is_active=True).order_by(Item.name).all():
                v = InventoryLayer.get_valuation(it.id)
                if v["total_qty"] > 0:
                    rd = [it.name, it.code, v["total_qty"],
                          round(v["avg_cost"],2) if v["avg_cost"] else 0,
                          round(v["total_value"],2), v["layer_count"]]
                    for col, val in enumerate(rd, 1):
                        ws.cell(row=ri, column=col, value=val)
                    style_row(ri, len(headers), alt=ri%2==0); ri += 1

        elif report_type == "audit":
            from app.services import AuditService
            ws.title = "ط³ط¬ظ„ ط§ظ„ط£ظˆط¯ظٹطھ"
            ws.merge_cells("A1:I1")
            ws["A1"] = f"ط³ط¬ظ„ طھط¯ظ‚ظٹظ‚ ط§ظ„ظ†ط¸ط§ظ… â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["#","ط§ظ„طھط§ط±ظٹط®","ط§ظ„ظ…ط³طھط®ط¯ظ…","ط§ظ„ط¥ط¬ط±ط§ط،","ط§ظ„ط¹ظ†طµط±","ط§ظ„ظˆطµظپ","IP","ط§ظ„ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ‚ط¯ظٹظ…ط©","ط§ظ„ط¨ظٹط§ظ†ط§طھ ط§ظ„ط¬ط¯ظٹط¯ط©"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            result = AuditService.get_logs(1, 5000, {})
            for ri, l in enumerate(result["items"], 3):
                rd = [l.id, l.created_date, l.user_name, l.action,
                      f"{l.resource}#{l.resource_id}" if l.resource_id else l.resource,
                      l.description or "", l.ip_address or "",
                      l.old_data or "", l.new_data or ""]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        elif report_type == "abc":
            ws.title = "طھط­ظ„ظٹظ„ ABC"
            ws.merge_cells("A1:F1")
            ws["A1"] = f"طھط­ظ„ظٹظ„ ABC ظ„ظ„ظ…ط®ط²ظˆظ† â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["ظƒظˆط¯ ط§ظ„طµظ†ظپ","ط§ظ„طµظ†ظپ","ط§ظ„ظپط¦ط©","ط§ظ„ظˆط­ط¯ط©","ط¥ط¬ظ…ط§ظ„ظٹ ط§ظ„ظƒظ…ظٹط©","ط³ط¹ط± ط§ظ„ظˆط­ط¯ط©","ط§ظ„ظ‚ظٹظ…ط©","%","طھط±ط§ظƒظ…ظٹ %","ط§ظ„طھطµظ†ظٹظپ"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            from app.routes import abc_analysis
            with current_app.test_request_context():
                resp = abc_analysis()
                result = resp.get_json()["data"]
            for ri, i in enumerate(result.get("items", []), 3):
                rd = [i["item_code"], i["item_name"], i["category"], i["unit"],
                      i["total_stock"], i["unit_price"], i["total_value"],
                      f"{i['pct']}%", f"{i['cumulative_pct']}%", i["class"]]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        elif report_type == "aging":
            ws.title = "ط¹ظ…ط± ط§ظ„ظ…ط®ط²ظˆظ†"
            ws.merge_cells("A1:L1")
            ws["A1"] = f"طھظ‚ط±ظٹط± ط¹ظ…ط± ط§ظ„ظ…ط®ط²ظˆظ† â€” {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["ظƒظˆط¯ ط§ظ„طµظ†ظپ","ط§ظ„طµظ†ظپ","ط§ظ„ظˆط­ط¯ط©","ط§ظ„ظƒظ…ظٹط©","ط§ظ„ظ‚ظٹظ…ط©","ط£ظ‚ط¯ظ… ظٹظˆظ…","0-30","31-60","61-90","91-180","181-365","365+"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=2, column=col, value=h)
            style_header(2, len(headers))
            from app.routes import inventory_aging
            with current_app.test_request_context():
                resp = inventory_aging()
                result = resp.get_json()["data"]
            for ri, i in enumerate(result.get("items", []), 3):
                b = i.get("qty_buckets",{})
                rd = [i["item_code"], i["item_name"], i["unit"],
                      i["total_qty"], i["total_value"], f"{i['oldest_days']} ظٹظˆظ…",
                      b.get("0-30",0), b.get("31-60",0), b.get("61-90",0),
                      b.get("91-180",0), b.get("181-365",0), b.get("365+",0)]
                for col, val in enumerate(rd, 1):
                    ws.cell(row=ri, column=col, value=val)
                style_row(ri, len(headers), alt=ri%2==0)

        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(width+4, 40)

        buf = io.BytesIO()
        wb.save(buf); buf.seek(0)
        return buf
