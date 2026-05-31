"""
طبقة الخدمات — Business Logic Services
كل المنطق التجاري معزول هنا بعيداً عن الـ routes
"""
import datetime, json
from sqlalchemy import func
from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import (db, User, Warehouse, Category, Supplier, Item,
                         Stock, StockMovement, Transfer, InventoryCount,
                         InventoryCountLine, Notification, AuditLog, Project,
                         PurchaseRequest, PRItem, ApprovalLog,
                         RFQ, RFQSupplier, Quotation, QuotationItem,
                         PurchaseOrder, POItem,
                         GoodsReceipt, GRNItem,
                         PurchaseReturn, PReturnItem,
                         SupplierEvaluation, SupplierProfile)
from app.utils import gen_ref, paginate, parse_date

# ══════════════════════════════════════════════════════════════
#  AUDIT SERVICE
# ══════════════════════════════════════════════════════════════
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
    def get_logs(page=1, per_page=50):
        q = AuditLog.query.order_by(AuditLog.created_at.desc())
        return paginate(q, page, per_page)


# ══════════════════════════════════════════════════════════════
#  NOTIFICATION SERVICE
# ══════════════════════════════════════════════════════════════
class NotificationService:
    @staticmethod
    def push(type_, title, message, ref_type=None, ref_id=None, roles=("admin","manager")):
        users = User.query.filter(User.role.in_(roles), User.is_active == True).all()
        for u in users:
            db.session.add(Notification(
                type=type_, title=title, message=message,
                user_id=u.id, ref_type=ref_type, ref_id=ref_id,
            ))

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
                    f"⚠️ مخزون منخفض: {item.name}",
                    f"الرصيد الإجمالي {total} {item.unit} — الحد الأدنى {item.min_quantity}",
                    ref_type="item", ref_id=item_id,
                )
                db.session.commit()


# ══════════════════════════════════════════════════════════════
#  AUTH SERVICE
# ══════════════════════════════════════════════════════════════
class AuthService:
    @staticmethod
    def login(username, password):
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        if not user or not user.check_password(password):
            AuditService.log("login_failed", "auth", desc=f"فشل دخول: {username}")
            db.session.commit()
            return None, "بيانات تسجيل الدخول غير صحيحة"
        if not user.is_active:
            return None, "الحساب موقوف — تواصل مع المسؤول"
        user.last_login = datetime.datetime.utcnow()
        AuditService.log("login", "auth", user.id, f"دخول: {user.name}")
        db.session.commit()
        return user, None

    @staticmethod
    def change_password(user_id, old_pw, new_pw):
        user = User.query.get(user_id)
        if not user:
            return False, "المستخدم غير موجود"
        if not user.check_password(old_pw):
            return False, "كلمة المرور الحالية غير صحيحة"
        if len(new_pw) < 6:
            return False, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
        user.set_password(new_pw)
        AuditService.log("update", "user", user_id, "تغيير كلمة المرور")
        db.session.commit()
        return True, None


# ══════════════════════════════════════════════════════════════
#  DASHBOARD SERVICE
# ══════════════════════════════════════════════════════════════
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
        day_names = ["الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
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
            },
            "warehouses":           wh_stats,
            "critical_items":       critical_items,
            "recent_movements":     [m.to_dict() for m in recent],
            "chart_data":           chart,
            "unread_notifications": unread,
        }


# ══════════════════════════════════════════════════════════════
#  ITEM SERVICE
# ══════════════════════════════════════════════════════════════
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
            return None, f"الكود '{data['code']}' مستخدم مسبقاً"
        if data.get("barcode") and Item.query.filter_by(barcode=data["barcode"]).first():
            return None, "الباركود مستخدم مسبقاً"

        item = Item(
            code          = data["code"],
            barcode       = data.get("barcode"),
            name          = data["name"],
            category_id   = data.get("category_id"),
            unit          = data.get("unit", "قطعة"),
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
                    user_id=user_id, notes="رصيد أولي",
                ))

        AuditService.log("create","item",item.id,f"إضافة صنف: {item.name}",new=data)
        db.session.commit()
        NotificationService.check_low_stock(item.id)
        return item, None

    @staticmethod
    def update(item_id, data, user_id):
        item = Item.query.get(item_id)
        if not item:
            return None, "الصنف غير موجود"
        old = item.to_dict(include_stock=False)
        for f in ["name","barcode","category_id","unit","min_quantity",
                  "reorder_point","unit_price","description","is_active"]:
            if f in data:
                setattr(item, f, data[f])
        AuditService.log("update","item",item_id,f"تحديث: {item.name}",old=old,new=data)
        db.session.commit()
        return item, None

    @staticmethod
    def delete(item_id):
        item = Item.query.get(item_id)
        if not item:
            return False, "الصنف غير موجود"
        item.is_active = False
        AuditService.log("delete","item",item_id,f"حذف: {item.name}")
        db.session.commit()
        return True, None


# ══════════════════════════════════════════════════════════════
#  MOVEMENT SERVICE
# ══════════════════════════════════════════════════════════════
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
            return None, "الصنف غير موجود"

        qty    = float(data["quantity"])
        wh_id  = int(data["warehouse_id"])
        mtype  = data["type"]

        if qty <= 0:
            return None, "الكمية يجب أن تكون أكبر من صفر"

        # Check sufficient stock for outbound/damage
        dec = {"out","damage"}
        inc = {"in","return"}
        if mtype in dec:
            stock   = Stock.query.filter_by(item_id=item.id, warehouse_id=wh_id).first()
            current = stock.quantity if stock else 0
            if current < qty:
                return None, (f"الكمية المطلوبة ({qty} {item.unit}) "
                              f"تتجاوز الرصيد المتاح ({current} {item.unit})")

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
        )
        db.session.add(mov)

        # Update stock
        stock = Stock.get_or_create(item.id, wh_id)
        stock.quantity += qty if mtype in inc else -qty

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
        if not item: return None, "الصنف غير موجود"
        wh = Warehouse.query.get(wh_id)
        if not wh: return None, "المخزن غير موجود"
        new_qty = float(data["new_quantity"])
        if new_qty < 0: return None, "الكمية لا يمكن أن تكون سالبة"
        stock = Stock.get_or_create(item.id, wh_id)
        current = stock.quantity
        diff = new_qty - current
        if diff == 0: return None, "الكمية الجديدة تساوي الكمية الحالية — لا يوجد تغيير"
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
                         f"تسوية: {item.name} {current} → {new_qty} {item.unit}")
        db.session.commit()
        NotificationService.check_low_stock(item.id)
        return mov, None


# ══════════════════════════════════════════════════════════════
#  TRANSFER SERVICE
# ══════════════════════════════════════════════════════════════
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
            return None, "مخزن المصدر والهدف لا يمكن أن يكونا متماثلين"

        item = Item.query.get(data.get("item_id"))
        if not item:
            return None, "الصنف غير موجود"

        qty = float(data["quantity"])
        stock = Stock.query.filter_by(
            item_id=item.id, warehouse_id=data["from_warehouse_id"]
        ).first()
        avail = stock.quantity if stock else 0
        if avail < qty:
            return None, f"الرصيد غير كافٍ — المتاح: {avail} {item.unit}"

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
        db.session.add(tr)
        db.session.flush()

        NotificationService.push(
            "transfer_request",
            f"🔄 طلب تحويل: {item.name}",
            f"طلب {qty} {item.unit} من {tr.from_wh.name} إلى {tr.to_wh.name}",
            ref_type="transfer", ref_id=tr.id,
        )
        AuditService.log("create","transfer",tr.id,
                         f"طلب تحويل: {item.name} {qty}")
        db.session.commit()
        return tr, None

    @staticmethod
    def approve(transfer_id, approver_id):
        tr = Transfer.query.get(transfer_id)
        if not tr:
            return None, "الطلب غير موجود"
        if tr.status != "pending":
            return None, "تمت معالجة هذا الطلب مسبقاً"

        sf = Stock.query.filter_by(item_id=tr.item_id,
                                    warehouse_id=tr.from_warehouse_id).first()
        if not sf or sf.quantity < tr.quantity:
            return None, "الرصيد غير كافٍ لتنفيذ التحويل"

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
            notes               = f"تحويل معتمد — {tr.ref_number}",
        )
        db.session.add(mov)
        db.session.flush()

        tr.status      = "executed"
        tr.approved_by = approver_id
        tr.approved_at = datetime.datetime.utcnow()
        tr.movement_id = mov.id

        AuditService.log("approve","transfer",transfer_id,f"اعتماد: {tr.ref_number}")
        db.session.commit()
        NotificationService.check_low_stock(tr.item_id)
        return tr, None

    @staticmethod
    def reject(transfer_id, approver_id, reason=""):
        tr = Transfer.query.get(transfer_id)
        if not tr:
            return None, "الطلب غير موجود"
        if tr.status != "pending":
            return None, "تمت معالجة هذا الطلب مسبقاً"

        tr.status        = "rejected"
        tr.approved_by   = approver_id
        tr.approved_at   = datetime.datetime.utcnow()
        tr.reject_reason = reason

        AuditService.log("reject","transfer",transfer_id,f"رفض: {tr.ref_number}")
        db.session.commit()
        return tr, None


# ══════════════════════════════════════════════════════════════
#  INVENTORY COUNT SERVICE
# ══════════════════════════════════════════════════════════════
class CountService:
    @staticmethod
    def get_list():
        return InventoryCount.query.order_by(InventoryCount.started_at.desc()).all()

    @staticmethod
    def create(data, user_id):
        wh_id = data.get("warehouse_id")
        if not wh_id:
            return None, "المخزن مطلوب"
        if InventoryCount.query.filter_by(warehouse_id=wh_id, status="active").first():
            return None, "يوجد جلسة جرد نشطة لهذا المخزن"

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

        AuditService.log("create","count",count.id,f"بدء جرد: {count.ref_number}")
        db.session.commit()
        return count, None

    @staticmethod
    def update_line(count_id, line_id, actual_qty, notes=""):
        line = InventoryCountLine.query.get(line_id)
        if not line or line.count_id != count_id:
            return None, "السطر غير موجود"
        line.actual_quantity = float(actual_qty)
        line.notes           = notes
        db.session.commit()
        return line, None

    @staticmethod
    def complete(count_id, user_id):
        count = InventoryCount.query.get(count_id)
        if not count:
            return None, "الجلسة غير موجودة"
        if count.status != "active":
            return None, "الجلسة غير نشطة"

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
                    notes        = f"تسوية جرد — {count.ref_number}",
                ))
                diffs += 1

        count.status       = "completed"
        count.completed_at = datetime.datetime.utcnow()

        if diffs > 0:
            NotificationService.push(
                "count_diff",
                f"⚖️ فروقات جرد: {count.warehouse.name}",
                f"{diffs} فروقات في {count.ref_number}",
                ref_type="count", ref_id=count.id,
            )

        AuditService.log("complete","count",count_id,
                         f"إغلاق جرد: {count.ref_number} — {diffs} فروقات")
        db.session.commit()
        return {"differences": diffs, "count": count}, None


# ══════════════════════════════════════════════════════════════
#  SUPPLIER SERVICE
# ══════════════════════════════════════════════════════════════
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
            return None, "اسم المورد مطلوب"
        s = Supplier(
            code          = data.get("code") or gen_ref("SUP"),
            name          = data["name"],
            category      = data.get("category"),
            phone         = data.get("phone"),
            email         = data.get("email"),
            address       = data.get("address"),
            tax_number    = data.get("tax_number"),
            payment_terms = data.get("payment_terms", "نقداً"),
            rating        = data.get("rating", 3),
            notes         = data.get("notes"),
        )
        db.session.add(s)
        AuditService.log("create","supplier",None,f"مورد: {s.name}")
        db.session.commit()
        return s, None

    @staticmethod
    def update(supplier_id, data):
        s = Supplier.query.get(supplier_id)
        if not s:
            return None, "المورد غير موجود"
        for f in ["name","category","phone","email","address",
                  "tax_number","payment_terms","rating","is_active","notes"]:
            if f in data:
                setattr(s, f, data[f])
        AuditService.log("update","supplier",supplier_id,f"تحديث: {s.name}")
        db.session.commit()
        return s, None


# ══════════════════════════════════════════════════════════════
#  USER SERVICE
# ══════════════════════════════════════════════════════════════
class UserService:
    @staticmethod
    def get_list():
        return User.query.filter_by(is_active=True).all()

    @staticmethod
    def create(data):
        errs = {}
        if not data.get("name"):     errs["name"]     = "الاسم مطلوب"
        if not data.get("username"): errs["username"]  = "اسم المستخدم مطلوب"
        if not data.get("password"): errs["password"]  = "كلمة المرور مطلوبة"
        elif len(data["password"]) < 6:
            errs["password"] = "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
        if errs:
            return None, errs
        if User.query.filter_by(username=data["username"]).first():
            return None, {"username": "اسم المستخدم مستخدم مسبقاً"}

        u = User(
            name         = data["name"],
            username     = data["username"],
            email        = data.get("email"),
            role         = data.get("role", "keeper"),
            warehouse_id = data.get("warehouse_id"),
        )
        u.set_password(data["password"])
        db.session.add(u)
        AuditService.log("create","user",None,f"مستخدم: {u.name}")
        db.session.commit()
        return u, None

    @staticmethod
    def update(user_id, data, current_user_id):
        if user_id == current_user_id and data.get("is_active") is False:
            return None, "لا يمكنك تعطيل حسابك الخاص"
        u = User.query.get(user_id)
        if not u:
            return None, "المستخدم غير موجود"
        for f in ["name","email","role","warehouse_id","is_active"]:
            if f in data:
                setattr(u, f, data[f])
        if data.get("password"):
            if len(data["password"]) < 6:
                return None, "كلمة المرور قصيرة جداً"
            u.set_password(data["password"])
        AuditService.log("update","user",user_id,f"تحديث: {u.name}")
        db.session.commit()
        return u, None


# ══════════════════════════════════════════════════════════════
#  PURCHASE ORDER SERVICE
# ══════════════════════════════════════════════════════════════
# procurement logic moved to routes.py

# ══════════════════════════════════════════════════════════════
#  STOCK INQUIRY SERVICE
# ══════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════
#  REPORT SERVICE
# ══════════════════════════════════════════════════════════════
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
            return None, "تاريخ غير صحيح"
        q = StockMovement.query
        if date_to:
            try:
                d2 = dt.datetime.strptime(date_to, "%Y-%m-%d").date() + dt.timedelta(days=1)
            except ValueError:
                return None, "تاريخ النهاية غير صحيح"
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
                "status_label":"نشط" if p.status=="active" else "متوقف",
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
            ws.title = "رصيد المخازن"
            whs = Warehouse.query.filter_by(is_active=True).all()
            ws.merge_cells(f"A1:{get_column_letter(5+len(whs))}1")
            ws["A1"] = f"تقرير رصيد المخازن — {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28

            headers = ["الكود","الصنف","الفئة","الوحدة"] + \
                      [wh.name for wh in whs] + ["الإجمالي","القيمة (ر.س)","الحالة"]
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
            ws.title = "سجل الحركات"
            headers = ["#","التاريخ","الوقت","الصنف","النوع","الكمية",
                       "الوحدة","المخزن","المنفذ","المرجع","المشروع","المهندس","ملاحظات"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=h)
            style_header(1, len(headers))
            tmap = {"in":"وارد","out":"صرف","transfer":"تحويل","adjustment":"تسوية",
                    "return":"مرتجع","damage":"هالك"}
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
            ws.title = "التحويلات"
            headers = ["#","رقم المرجع","الصنف","الكمية","الوحدة","من مخزن","إلى مخزن","الطالب","التاريخ","السبب","الحالة"]
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
            ws.title = "فروقات الجرد"
            headers = ["#","الصنف","كود الصنف","المخزن","كمية النظام","الكمية الفعلية","الفرق","ملاحظات","تاريخ الجرد"]
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
            ws.title = "الميزانية"
            ws.merge_cells("A1:H1")
            ws["A1"] = f"تقرير ميزانية المشاريع — {datetime.datetime.now().strftime('%d/%m/%Y')}"
            ws["A1"].font = Font(bold=True, size=14, color="1B4F72")
            ws["A1"].alignment = ca
            ws.row_dimensions[1].height = 28
            headers = ["المشروع","الكود","العميل","الميزانية","المنصرف","المتبقي","الاستخدام %","الحالة"]
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
            ws.cell(row=sr, column=1, value="الإجمالي").font = Font(bold=True)
            ws.cell(row=sr, column=4, value=data["summary"]["total_budget"]).number_format = '#,##0.00'
            ws.cell(row=sr, column=5, value=data["summary"]["total_spent"]).number_format = '#,##0.00'
            ws.cell(row=sr, column=6, value=data["summary"]["total_remaining"]).number_format = '#,##0.00'
            for c in range(1, len(headers)+1):
                ws.cell(row=sr, column=c).border = bdr
                ws.cell(row=sr, column=c).font = Font(bold=True)

        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(width+4, 40)

        buf = io.BytesIO()
        wb.save(buf); buf.seek(0)
        return buf
