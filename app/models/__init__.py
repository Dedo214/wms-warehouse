"""نماذج قاعدة البيانات"""
import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, CheckConstraint
from sqlalchemy.orm import validates

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    username      = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(160), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  default="keeper")
    warehouse_id  = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=True)
    is_active     = db.Column(db.Boolean, default=True)
    last_login    = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    warehouse  = db.relationship("Warehouse", foreign_keys=[warehouse_id], back_populates="users")
    movements  = db.relationship("StockMovement", back_populates="user", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")
    ROLE_PERMISSIONS = {
        "super_admin": ["view","create","update","delete","approve","export","manage_users","manage_system"],
        "admin":       ["view","create","update","delete","approve","export","manage_users"],
        "manager":     ["view","create","update","approve","export"],
        "purchasing":  ["view","create","update","approve","export"],
        "keeper":      ["view","create"],
        "viewer":      ["view"],
    }
    def set_password(self, raw): self.password_hash = generate_password_hash(raw)
    def check_password(self, raw): return check_password_hash(self.password_hash, raw)
    def get_permissions(self): return self.ROLE_PERMISSIONS.get(self.role, ["view"])
    def has_permission(self, p): return p in self.get_permissions()
    def can_approve(self): return self.role in ("admin","manager")
    def to_dict(self):
        rl = {"super_admin":"مدير النظام","admin":"مدير عام","manager":"مشرف","purchasing":"مشتريات","keeper":"أمين مخزن","viewer":"قارئ"}
        return {"id":self.id,"name":self.name,"username":self.username,"email":self.email,
                "role":self.role,"role_label":rl.get(self.role,self.role),
                "warehouse_id":self.warehouse_id,
                "warehouse_name":self.warehouse.name if self.warehouse else "الكل",
                "is_active":self.is_active,"permissions":self.get_permissions(),
                "last_login":self.last_login.isoformat() if self.last_login else None,
                "created_at":self.created_at.isoformat(),"avatar":self.name[:2]}

class Warehouse(db.Model):
    __tablename__ = "warehouses"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    code       = db.Column(db.String(30),  unique=True)
    location   = db.Column(db.String(300))
    capacity   = db.Column(db.Integer, default=1000)
    type       = db.Column(db.String(20), default="sub")
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    users  = db.relationship("User", foreign_keys="User.warehouse_id", back_populates="warehouse")
    stocks = db.relationship("Stock", back_populates="warehouse", cascade="all,delete-orphan")
    def get_item_count(self):
        return db.session.query(func.count(Stock.id)).filter(
            Stock.warehouse_id==self.id, Stock.quantity>0).scalar() or 0
    def to_dict(self):
        return {"id":self.id,"name":self.name,"code":self.code,"location":self.location,
                "capacity":self.capacity,"type":self.type,"is_active":self.is_active,
                "item_count":self.get_item_count(),"created_at":self.created_at.isoformat()}

class Category(db.Model):
    __tablename__ = "categories"
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(20), default="#3498db")
    icon  = db.Column(db.String(10), default="📦")
    items = db.relationship("Item", back_populates="category", lazy="dynamic")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"color":self.color,"icon":self.icon,
                "item_count":self.items.filter_by(is_active=True).count()}

class Supplier(db.Model):
    __tablename__ = "suppliers"
    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(30), unique=True)
    name          = db.Column(db.String(160), nullable=False)
    category      = db.Column(db.String(100))
    phone         = db.Column(db.String(30))
    email         = db.Column(db.String(160))
    address       = db.Column(db.String(300))
    tax_number    = db.Column(db.String(50))
    payment_terms = db.Column(db.String(50), default="نقداً")
    rating        = db.Column(db.Integer, default=3)
    is_active     = db.Column(db.Boolean, default=True)
    notes         = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    movements = db.relationship("StockMovement", back_populates="supplier", lazy="dynamic")
    def to_dict(self):
        count = self.movements.count()
        last  = self.movements.order_by(StockMovement.created_at.desc()).first()
        return {"id":self.id,"code":self.code,"name":self.name,"category":self.category,
                "phone":self.phone,"email":self.email,"address":self.address,
                "tax_number":self.tax_number,"payment_terms":self.payment_terms,
                "rating":self.rating,"is_active":self.is_active,"notes":self.notes,
                "supply_count":count,"last_supply":last.created_at.strftime("%d/%m/%Y") if last else "—",
                "created_at":self.created_at.isoformat()}

class Item(db.Model):
    __tablename__ = "items"
    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(60), unique=True, nullable=False, index=True)
    barcode       = db.Column(db.String(120), unique=True, index=True)
    name          = db.Column(db.String(200), nullable=False)
    category_id   = db.Column(db.Integer, db.ForeignKey("categories.id"))
    unit          = db.Column(db.String(30), default="قطعة")
    min_quantity  = db.Column(db.Float, default=0.0)
    reorder_point = db.Column(db.Float, default=0.0)
    unit_price    = db.Column(db.Float, default=0.0)
    description   = db.Column(db.Text)
    image_url     = db.Column(db.String(500))
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    category  = db.relationship("Category", back_populates="items")
    stocks    = db.relationship("Stock", back_populates="item", cascade="all,delete-orphan")
    movements = db.relationship("StockMovement", back_populates="item", lazy="dynamic")
    transfers = db.relationship("Transfer", back_populates="item", lazy="dynamic")
    def get_total_stock(self): return sum(s.quantity for s in self.stocks)
    def get_stock_in(self, wh_id):
        s = next((s for s in self.stocks if s.warehouse_id==wh_id), None)
        return float(s.quantity) if s else 0.0
    def get_status(self):
        total = self.get_total_stock()
        if self.min_quantity > 0:
            if total <= self.min_quantity: return "critical"
            if total <= self.min_quantity * 1.3: return "warning"
        return "ok"
    def get_status_label(self):
        return {"critical":"حرج","warning":"تحذير","ok":"جيد"}[self.get_status()]
    def to_dict(self, include_stock=True):
        d = {"id":self.id,"code":self.code,"barcode":self.barcode,"name":self.name,
             "category_id":self.category_id,
             "category_name":self.category.name if self.category else "",
             "category_icon":self.category.icon if self.category else "📦",
             "unit":self.unit,"min_quantity":self.min_quantity,
             "reorder_point":self.reorder_point,"unit_price":self.unit_price,
              "description":self.description,"image_url":self.image_url,"is_active":self.is_active,
             "created_at":self.created_at.isoformat()}
        if include_stock:
            whs = Warehouse.query.filter_by(is_active=True).all()
            d["warehouse_stocks"] = [{"warehouse_id":wh.id,"warehouse_name":wh.name,
                "quantity":self.get_stock_in(wh.id)} for wh in whs]
            d["total_stock"] = self.get_total_stock()
            d["total_value"] = round(d["total_stock"] * self.unit_price, 2)
            status = self.get_status()
            d["status"] = status
            d["status_label"] = {"critical":"حرج","warning":"تحذير","ok":"جيد"}[status]
        return d

class Stock(db.Model):
    __tablename__ = "stock"
    id           = db.Column(db.Integer, primary_key=True)
    item_id      = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    quantity     = db.Column(db.Float, default=0.0)
    item      = db.relationship("Item", back_populates="stocks")
    warehouse = db.relationship("Warehouse", back_populates="stocks")
    __table_args__ = (db.UniqueConstraint("item_id","warehouse_id"),
                      db.CheckConstraint("quantity >= 0", name="ck_stock_quantity_non_negative"),)
    @classmethod
    def get_or_create(cls, item_id, warehouse_id):
        obj = cls.query.filter_by(item_id=item_id, warehouse_id=warehouse_id).first()
        if not obj:
            obj = cls(item_id=item_id, warehouse_id=warehouse_id, quantity=0.0)
            db.session.add(obj)
        return obj

    @validates("quantity")
    def validate_quantity(self, key, value):
        if value is not None and value < 0:
            raise ValueError("الكمية لا يمكن أن تكون سالبة")
        return value

class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    id                  = db.Column(db.Integer, primary_key=True)
    ref_number          = db.Column(db.String(60), unique=True)
    type                = db.Column(db.String(20), nullable=False)
    item_id             = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    warehouse_id        = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    target_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    quantity            = db.Column(db.Float, nullable=False)
    unit_price          = db.Column(db.Float, default=0.0)
    supplier_id         = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    user_id             = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes               = db.Column(db.Text)
    project             = db.Column(db.String(200))
    engineer_name       = db.Column(db.String(200))
    lot_number          = db.Column(db.String(100))
    created_at          = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    item             = db.relationship("Item", foreign_keys=[item_id], back_populates="movements")
    warehouse        = db.relationship("Warehouse", foreign_keys=[warehouse_id])
    target_warehouse = db.relationship("Warehouse", foreign_keys=[target_warehouse_id])
    user             = db.relationship("User", foreign_keys=[user_id], back_populates="movements")
    supplier         = db.relationship("Supplier", foreign_keys=[supplier_id], back_populates="movements")
    TYPE_LABELS = {"in":"وارد","out":"صرف","transfer":"تحويل","adjustment":"تسوية","return":"مرتجع","damage":"هالك"}
    def to_dict(self):
        return {"id":self.id,"ref_number":self.ref_number,"type":self.type,
                "type_label":self.TYPE_LABELS.get(self.type,self.type),
                "item_id":self.item_id,"item_name":self.item.name if self.item else "",
                "item_code":self.item.code if self.item else "",
                "item_unit":self.item.unit if self.item else "",
                "warehouse_id":self.warehouse_id,
                "warehouse_name":self.warehouse.name if self.warehouse else "",
                "target_warehouse_id":self.target_warehouse_id,
                "target_warehouse_name":self.target_warehouse.name if self.target_warehouse else "",
                "quantity":self.quantity,"unit_price":self.unit_price,
                "total_value":round(self.quantity*self.unit_price,2),
                "supplier_name":self.supplier.name if self.supplier else "",
                "user_name":self.user.name if self.user else "",
                "notes":self.notes,"project":self.project,
                "engineer_name":self.engineer_name or "",
                "lot_number":self.lot_number or "",
                "created_at":self.created_at.isoformat(),
                "created_date":self.created_at.strftime("%d/%m/%Y"),
                "created_time":self.created_at.strftime("%H:%M")}

class Transfer(db.Model):
    __tablename__ = "transfers"
    id                = db.Column(db.Integer, primary_key=True)
    ref_number        = db.Column(db.String(60), unique=True)
    item_id           = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    to_warehouse_id   = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    quantity          = db.Column(db.Float, nullable=False)
    reason            = db.Column(db.Text)
    status            = db.Column(db.String(20), default="pending")
    requested_by      = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by       = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at       = db.Column(db.DateTime)
    reject_reason     = db.Column(db.Text)
    movement_id       = db.Column(db.Integer, db.ForeignKey("stock_movements.id"))
    approval_chain_id = db.Column(db.Integer, db.ForeignKey("approval_chains.id"))
    current_step      = db.Column(db.Integer, default=0)
    created_at        = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    item      = db.relationship("Item", foreign_keys=[item_id], back_populates="transfers")
    from_wh   = db.relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_wh     = db.relationship("Warehouse", foreign_keys=[to_warehouse_id])
    requester = db.relationship("User", foreign_keys=[requested_by])
    approver  = db.relationship("User", foreign_keys=[approved_by])
    STATUS_LABELS = {"pending":"معلق","executed":"منفذ","rejected":"مرفوض"}
    def to_dict(self):
        chain = ApprovalChain.query.get(self.approval_chain_id) if self.approval_chain_id else None
        return {"id":self.id,"ref_number":self.ref_number,
                "item_id":self.item_id,"item_name":self.item.name if self.item else "",
                "item_unit":self.item.unit if self.item else "",
                "from_warehouse_id":self.from_warehouse_id,
                "from_warehouse_name":self.from_wh.name if self.from_wh else "",
                "to_warehouse_id":self.to_warehouse_id,
                "to_warehouse_name":self.to_wh.name if self.to_wh else "",
                "quantity":self.quantity,"reason":self.reason,"status":self.status,
                "status_label":self.STATUS_LABELS.get(self.status,self.status),
                "requester_name":self.requester.name if self.requester else "",
                "approver_name":self.approver.name if self.approver else "",
                "approved_at":self.approved_at.isoformat() if self.approved_at else None,
                "reject_reason":self.reject_reason,
                "approval_chain_id":self.approval_chain_id,
                "current_step":self.current_step or 0,
                "chain_steps":[s.to_dict() for s in chain.steps] if chain else [],
                "created_at":self.created_at.isoformat(),
                "created_date":self.created_at.strftime("%d/%m/%Y")}

class InventoryCount(db.Model):
    __tablename__ = "inventory_counts"
    id            = db.Column(db.Integer, primary_key=True)
    ref_number    = db.Column(db.String(60), unique=True)
    warehouse_id  = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    supervisor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    status        = db.Column(db.String(20), default="active")
    notes         = db.Column(db.Text)
    started_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    completed_at  = db.Column(db.DateTime)
    warehouse  = db.relationship("Warehouse")
    supervisor = db.relationship("User")
    lines      = db.relationship("InventoryCountLine", back_populates="count", cascade="all,delete-orphan")
    def get_progress(self):
        total   = len(self.lines)
        counted = sum(1 for l in self.lines if l.actual_quantity is not None)
        return round(counted/total*100) if total > 0 else 0
    def get_differences(self):
        return sum(1 for l in self.lines
                   if l.actual_quantity is not None and l.actual_quantity != l.system_quantity)
    def to_dict(self, include_lines=True):
        total   = len(self.lines)
        counted = sum(1 for l in self.lines if l.actual_quantity is not None)
        d = {"id":self.id,"ref_number":self.ref_number,
             "warehouse_id":self.warehouse_id,
             "warehouse_name":self.warehouse.name if self.warehouse else "",
             "supervisor_name":self.supervisor.name if self.supervisor else "",
             "status":self.status,
             "status_label":{"active":"جارٍ","completed":"مكتمل","cancelled":"ملغى"}.get(self.status),
             "notes":self.notes,"total_lines":total,"counted_lines":counted,
             "differences":self.get_differences(),"progress":self.get_progress(),
             "started_at":self.started_at.isoformat(),
             "completed_at":self.completed_at.isoformat() if self.completed_at else None}
        if include_lines:
            d["lines"] = [l.to_dict() for l in self.lines]
        return d

class InventoryCountLine(db.Model):
    __tablename__ = "inventory_count_lines"
    id              = db.Column(db.Integer, primary_key=True)
    count_id        = db.Column(db.Integer, db.ForeignKey("inventory_counts.id"), nullable=False)
    item_id         = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    system_quantity = db.Column(db.Float, nullable=False)
    actual_quantity = db.Column(db.Float)
    notes           = db.Column(db.Text)
    count = db.relationship("InventoryCount", back_populates="lines")
    item  = db.relationship("Item")
    @property
    def difference(self):
        if self.actual_quantity is None: return None
        return round(self.actual_quantity - self.system_quantity, 4)
    def to_dict(self):
        return {"id":self.id,"count_id":self.count_id,"item_id":self.item_id,
                "item_name":self.item.name if self.item else "",
                "item_code":self.item.code if self.item else "",
                "item_unit":self.item.unit if self.item else "",
                "system_quantity":self.system_quantity,"actual_quantity":self.actual_quantity,
                "difference":self.difference,"notes":self.notes}

class Notification(db.Model):
    __tablename__ = "notifications"
    id         = db.Column(db.Integer, primary_key=True)
    type       = db.Column(db.String(50), nullable=False)
    title      = db.Column(db.String(250), nullable=False)
    message    = db.Column(db.Text)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_read    = db.Column(db.Boolean, default=False)
    ref_type   = db.Column(db.String(50))
    ref_id     = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    user = db.relationship("User")
    def time_ago(self):
        diff = datetime.datetime.utcnow() - self.created_at
        s = diff.total_seconds()
        if s < 60:    return "منذ لحظات"
        if s < 3600:  return f"منذ {int(s/60)} دقيقة"
        if s < 86400: return f"منذ {int(s/3600)} ساعة"
        return f"منذ {int(s/86400)} يوم"
    def to_dict(self):
        return {"id":self.id,"type":self.type,"title":self.title,"message":self.message,
                "user_id":self.user_id,"is_read":self.is_read,"ref_type":self.ref_type,
                "ref_id":self.ref_id,"time_ago":self.time_ago(),
                "created_at":self.created_at.isoformat()}

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"))
    action      = db.Column(db.String(80), nullable=False)
    resource    = db.Column(db.String(80))
    resource_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    old_data    = db.Column(db.Text)
    new_data    = db.Column(db.Text)
    ip_address  = db.Column(db.String(50))
    user_agent  = db.Column(db.String(300))
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    user = db.relationship("User", back_populates="audit_logs")
    def to_dict(self):
        return {"id":self.id,"user_name":self.user.name if self.user else "نظام",
                "user_id":self.user_id,
                "action":self.action,"resource":self.resource,"resource_id":self.resource_id,
                "description":self.description,
                "old_data":self.old_data,"new_data":self.new_data,
                "ip_address":self.ip_address,
                "created_at":self.created_at.isoformat(),
                "created_date":self.created_at.strftime("%d/%m/%Y %H:%M")}

class ItemAttachment(db.Model):
    __tablename__ = "item_attachments"
    id         = db.Column(db.Integer, primary_key=True)
    item_id    = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    filename   = db.Column(db.String(300), nullable=False)
    original_name = db.Column(db.String(300), nullable=False)
    file_type  = db.Column(db.String(50))
    file_size  = db.Column(db.Integer, default=0)
    notes      = db.Column(db.Text)
    uploaded_by= db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    item = db.relationship("Item")
    uploader = db.relationship("User")
    def to_dict(self):
        return {"id":self.id,"item_id":self.item_id,"filename":self.filename,
                "original_name":self.original_name,"file_type":self.file_type,
                "file_size":self.file_size,"notes":self.notes,
                "uploaded_by_name":self.uploader.name if self.uploader else "",
                "created_at":self.created_at.isoformat(),
                "created_date":self.created_at.strftime("%d/%m/%Y")}

class NotificationConfig(db.Model):
    __tablename__ = "notification_configs"
    id      = db.Column(db.Integer, primary_key=True)
    key     = db.Column(db.String(100), unique=True, nullable=False)
    value   = db.Column(db.Text)
    def to_dict(self): return {"key":self.key,"value":self.value}

class BackupConfig(db.Model):
    __tablename__ = "backup_configs"
    id      = db.Column(db.Integer, primary_key=True)
    key     = db.Column(db.String(100), unique=True, nullable=False)
    value   = db.Column(db.Text)
    def to_dict(self): return {"key":self.key,"value":self.value}

class Project(db.Model):
    __tablename__ = "projects"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    code        = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    status      = db.Column(db.String(20), default="active")
    budget      = db.Column(db.Float, default=0.0)
    actual_cost = db.Column(db.Float, default=0.0)
    completion_pct = db.Column(db.Float, default=0.0)
    client      = db.Column(db.String(200))
    location    = db.Column(db.String(200))
    start_date  = db.Column(db.DateTime)
    end_date    = db.Column(db.DateTime)
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    invoices = db.relationship("ProjectInvoice", back_populates="project", cascade="all,delete-orphan")
    def get_invoice_total(self):
        return sum(i.amount for i in self.invoices if i.status != "cancelled")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"code":self.code or "",
                "description":self.description or "","status":self.status,
                "budget":self.budget,"actual_cost":self.actual_cost,
                "completion_pct":self.completion_pct,
                "client":self.client or "","location":self.location or "",
                "start_date":self.start_date.isoformat() if self.start_date else "",
                "end_date":self.end_date.isoformat() if self.end_date else "",
                "created_at":self.created_at.isoformat() if self.created_at else "",
                "invoice_total":self.get_invoice_total(),
                "invoices":[i.to_dict() for i in self.invoices]}

class ProjectInvoice(db.Model):
    __tablename__ = "project_invoices"
    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    ref_number  = db.Column(db.String(60))
    amount      = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    status      = db.Column(db.String(20), default="pending")
    invoice_date= db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    project = db.relationship("Project", back_populates="invoices")
    def to_dict(self):
        return {"id":self.id,"project_id":self.project_id,
                "ref_number":self.ref_number or "","amount":self.amount,
                "description":self.description or "","status":self.status,
                "invoice_date":self.invoice_date.isoformat()[:10] if self.invoice_date else "",
                "created_at":self.created_at.isoformat() if self.created_at else "",
                "status_label":{"pending":"قيد الانتظار","approved":"معتمد","paid":"مدفوع","cancelled":"ملغي"}.get(self.status,self.status)}


class ScheduledCount(db.Model):
    __tablename__ = "scheduled_counts"
    id           = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    frequency    = db.Column(db.String(20), default="monthly")  # weekly, monthly, quarterly
    day_of_month = db.Column(db.Integer, default=1)
    day_of_week  = db.Column(db.Integer, default=0)  # 0=Monday
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_created = db.Column(db.DateTime)
    warehouse = db.relationship("Warehouse")
    def to_dict(self):
        return {"id":self.id,"warehouse_id":self.warehouse_id,
                "warehouse_name":self.warehouse.name if self.warehouse else "",
                "frequency":self.frequency,"day_of_month":self.day_of_month,
                "day_of_week":self.day_of_week,"is_active":self.is_active,
                "last_created":self.last_created.isoformat() if self.last_created else None}
class PurchaseRequest(db.Model):
    __tablename__ = "purchase_requests"
    id           = db.Column(db.Integer, primary_key=True)
    ref_number   = db.Column(db.String(60), unique=True)
    request_date = db.Column(db.Date, default=datetime.datetime.utcnow)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    project_id   = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    department   = db.Column(db.String(100))
    priority     = db.Column(db.String(20), default="medium")
    required_date= db.Column(db.Date, nullable=True)
    notes        = db.Column(db.Text)
    status        = db.Column(db.String(20), default="draft")
    approval_chain_id = db.Column(db.Integer, db.ForeignKey("approval_chains.id"))
    current_step      = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    requester = db.relationship("User", foreign_keys=[requester_id])
    project   = db.relationship("Project", foreign_keys=[project_id])
    items     = db.relationship("PRItem", back_populates="pr", cascade="all,delete-orphan")
    STATUS_LABELS = {"draft":"مسودة","pending":"قيد المراجعة","approved":"معتمد","rejected":"مرفوض","cancelled":"ملغي"}
    def to_dict(self):
        return {"id":self.id,"ref_number":self.ref_number,
                "request_date":self.request_date.isoformat() if self.request_date else "",
                "requester_id":self.requester_id,
                "requester_name":self.requester.name if self.requester else "",
                "project_id":self.project_id,
                "project_name":self.project.name if self.project else "",
                "department":self.department or "",
                "priority":self.priority,
                "required_date":self.required_date.isoformat() if self.required_date else "",
                "notes":self.notes or "",
                "status":self.status,
                "status_label":self.STATUS_LABELS.get(self.status,self.status),
                "item_count":len(self.items),
                "items":[i.to_dict() for i in self.items],
                "created_at":self.created_at.isoformat()}

class PRItem(db.Model):
    __tablename__ = "pr_items"
    id            = db.Column(db.Integer, primary_key=True)
    pr_id         = db.Column(db.Integer, db.ForeignKey("purchase_requests.id"))
    item_name     = db.Column(db.String(200))
    category      = db.Column(db.String(100))
    unit          = db.Column(db.String(30))
    quantity      = db.Column(db.Float)
    current_stock = db.Column(db.Float, default=0)
    min_stock     = db.Column(db.Float, default=0)
    estimated_cost= db.Column(db.Float, default=0)
    notes         = db.Column(db.Text)
    pr            = db.relationship("PurchaseRequest", back_populates="items")
    def to_dict(self):
        return {"id":self.id,"pr_id":self.pr_id,"item_name":self.item_name or "",
                "category":self.category or "","unit":self.unit or "",
                "quantity":self.quantity,"current_stock":self.current_stock,
                "min_stock":self.min_stock,"estimated_cost":self.estimated_cost,
                "total":round((self.quantity or 0)*(self.estimated_cost or 0),2),
                "notes":self.notes or ""}

class ApprovalLog(db.Model):
    __tablename__ = "approval_logs"
    id           = db.Column(db.Integer, primary_key=True)
    resource_type= db.Column(db.String(50))
    resource_id  = db.Column(db.Integer)
    level        = db.Column(db.Integer)
    approver_id  = db.Column(db.Integer, db.ForeignKey("users.id"))
    status       = db.Column(db.String(20))
    notes        = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    approver     = db.relationship("User", foreign_keys=[approver_id])
    STATUS_LABELS = {"approved":"معتمد","rejected":"مرفوض","returned":"معاد"}
    def to_dict(self):
        return {"id":self.id,"resource_type":self.resource_type,
                "resource_id":self.resource_id,"level":self.level,
                "approver_id":self.approver_id,
                "approver_name":self.approver.name if self.approver else "",
                "status":self.status,
                "status_label":self.STATUS_LABELS.get(self.status,self.status),
                "notes":self.notes or "",
                "created_at":self.created_at.isoformat()}

class RFQ(db.Model):
    __tablename__ = "rfqs"
    id            = db.Column(db.Integer, primary_key=True)
    ref_number    = db.Column(db.String(60), unique=True)
    pr_id         = db.Column(db.Integer, db.ForeignKey("purchase_requests.id"), nullable=True)
    valid_until   = db.Column(db.Date, nullable=True)
    delivery_terms= db.Column(db.Text)
    payment_terms = db.Column(db.String(200))
    warranty      = db.Column(db.String(200))
    notes         = db.Column(db.Text)
    status        = db.Column(db.String(20), default="draft")
    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    pr        = db.relationship("PurchaseRequest", foreign_keys=[pr_id])
    suppliers = db.relationship("RFQSupplier", back_populates="rfq", cascade="all,delete-orphan")
    quotations= db.relationship("Quotation", back_populates="rfq", cascade="all,delete-orphan")
    STATUS_LABELS = {"draft":"مسودة","sent":"مرسل","responded":"تم الرد","closed":"مغلق"}
    def to_dict(self):
        return {"id":self.id,"ref_number":self.ref_number,
                "pr_id":self.pr_id,
                "pr_ref":self.pr.ref_number if self.pr else "",
                "valid_until":self.valid_until.isoformat() if self.valid_until else "",
                "delivery_terms":self.delivery_terms or "",
                "payment_terms":self.payment_terms or "",
                "warranty":self.warranty or "",
                "notes":self.notes or "",
                "status":self.status,
                "status_label":self.STATUS_LABELS.get(self.status,self.status),
                "items":[i.to_dict() for i in self.items],
                "suppliers":[s.to_dict() for s in self.suppliers],
                "quotations":[q.to_dict() for q in self.quotations],
                "suppliers_count":len(self.suppliers),
                "quotations_count":len(self.quotations),
                "created_at":self.created_at.isoformat()}

class RFQSupplier(db.Model):
    __tablename__ = "rfq_suppliers"
    id         = db.Column(db.Integer, primary_key=True)
    rfq_id     = db.Column(db.Integer, db.ForeignKey("rfqs.id"))
    supplier_id= db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    emailed    = db.Column(db.Boolean, default=False)
    whatsapped = db.Column(db.Boolean, default=False)
    responded  = db.Column(db.Boolean, default=False)
    rfq      = db.relationship("RFQ", back_populates="suppliers")
    supplier = db.relationship("Supplier")
    def to_dict(self):
        return {"id":self.id,"rfq_id":self.rfq_id,
                "supplier_id":self.supplier_id,
                "supplier_name":self.supplier.name if self.supplier else "",
                "emailed":self.emailed,"whatsapped":self.whatsapped,
                "responded":self.responded}

class RFQItem(db.Model):
    __tablename__ = "rfq_items"
    id        = db.Column(db.Integer, primary_key=True)
    rfq_id    = db.Column(db.Integer, db.ForeignKey("rfqs.id"))
    item_name = db.Column(db.String(200))
    quantity  = db.Column(db.Float)
    unit      = db.Column(db.String(20))
    notes     = db.Column(db.Text)
    rfq   = db.relationship("RFQ", backref="items")
    def to_dict(self):
        return {"id":self.id,"rfq_id":self.rfq_id,
                "item_name":self.item_name or "",
                "quantity":self.quantity,"unit":self.unit or "",
                "notes":self.notes or ""}

class Quotation(db.Model):
    __tablename__ = "quotations"
    id           = db.Column(db.Integer, primary_key=True)
    ref_number   = db.Column(db.String(60))
    rfq_id       = db.Column(db.Integer, db.ForeignKey("rfqs.id"))
    supplier_id  = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    amount       = db.Column(db.Float, default=0)
    vat          = db.Column(db.Float, default=0)
    delivery_cost= db.Column(db.Float, default=0)
    total        = db.Column(db.Float)
    delivery_days= db.Column(db.Integer)
    warranty_period= db.Column(db.String(100))
    valid_until  = db.Column(db.Date)
    file         = db.Column(db.String(300))
    status       = db.Column(db.String(20), default="pending")
    notes        = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    rfq      = db.relationship("RFQ", back_populates="quotations")
    supplier = db.relationship("Supplier")
    items    = db.relationship("QuotationItem", back_populates="quotation", cascade="all,delete-orphan")
    STATUS_LABELS = {"pending":"قيد المراجعة","accepted":"مقبول","rejected":"مرفوض"}
    def to_dict(self):
        return {"id":self.id,"ref_number":self.ref_number,
                "rfq_id":self.rfq_id,
                "rfq_ref":self.rfq.ref_number if self.rfq else "",
                "supplier_id":self.supplier_id,
                "supplier_name":self.supplier.name if self.supplier else "",
                "amount":self.amount,"vat":self.vat,
                "delivery_cost":self.delivery_cost,"total":self.total or 0,
                "delivery_days":self.delivery_days,
                "warranty_period":self.warranty_period or "",
                "valid_until":self.valid_until.isoformat() if self.valid_until else "",
                "file":self.file or "","status":self.status,
                "status_label":self.STATUS_LABELS.get(self.status,self.status),
                "notes":self.notes or "",
                "items":[i.to_dict() for i in self.items],
                "created_at":self.created_at.isoformat()}

class QuotationItem(db.Model):
    __tablename__ = "quotation_items"
    id          = db.Column(db.Integer, primary_key=True)
    quotation_id= db.Column(db.Integer, db.ForeignKey("quotations.id"))
    item_name   = db.Column(db.String(200))
    quantity    = db.Column(db.Float)
    unit_price  = db.Column(db.Float)
    total       = db.Column(db.Float)
    quotation = db.relationship("Quotation", back_populates="items")
    def to_dict(self):
        return {"id":self.id,"quotation_id":self.quotation_id,
                "item_name":self.item_name or "","quantity":self.quantity,
                "unit_price":self.unit_price,"total":self.total or 0}

class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"
    id            = db.Column(db.Integer, primary_key=True)
    ref_number    = db.Column(db.String(60), unique=True)
    quotation_id  = db.Column(db.Integer, db.ForeignKey("quotations.id"), nullable=True)
    supplier_id   = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    project_id    = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    warehouse_id  = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    created_by    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    total_amount  = db.Column(db.Float, default=0.0)
    order_date    = db.Column(db.Date)
    delivery_date = db.Column(db.Date, nullable=True)
    currency      = db.Column(db.String(10), default="SAR")
    payment_terms = db.Column(db.String(200))
    notes         = db.Column(db.Text)
    status        = db.Column(db.String(20), default="draft")
    approval_chain_id = db.Column(db.Integer, db.ForeignKey("approval_chains.id"), nullable=True)
    current_step      = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    quotation = db.relationship("Quotation", foreign_keys=[quotation_id])
    supplier  = db.relationship("Supplier", foreign_keys=[supplier_id])
    project   = db.relationship("Project", foreign_keys=[project_id])
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])
    creator   = db.relationship("User", foreign_keys=[created_by])
    items     = db.relationship("POItem", back_populates="po", cascade="all,delete-orphan")
    receipts  = db.relationship("GoodsReceipt", back_populates="po", cascade="all,delete-orphan")
    STATUS_LABELS = {"draft":"مسودة","approved":"معتمد","sent":"مرسل","partial":"استلام جزئي","completed":"مكتمل","cancelled":"ملغي"}
    def to_dict(self):
        items_total = sum((i.total or 0) for i in self.items)
        chain_steps = []
        if self.approval_chain_id:
            chain = ApprovalChain.query.get(self.approval_chain_id)
            if chain: chain_steps = [s.to_dict() for s in chain.steps]
        return {"id":self.id,"ref_number":self.ref_number,
                "quotation_id":self.quotation_id,
                "quotation_ref":self.quotation.ref_number if self.quotation else "",
                "supplier_id":self.supplier_id,
                "supplier_name":self.supplier.name if self.supplier else "",
                "project_id":self.project_id,
                "project_name":self.project.name if self.project else "",
                "warehouse_id":self.warehouse_id,
                "warehouse_name":self.warehouse.name if self.warehouse else "",
                "created_by":self.created_by,
                "creator_name":self.creator.name if self.creator else "",
                "total_amount":self.total_amount or items_total,
                "order_date":self.order_date.isoformat() if self.order_date else "",
                "delivery_date":self.delivery_date.isoformat() if self.delivery_date else "",
                "currency":self.currency,"payment_terms":self.payment_terms or "",
                "notes":self.notes or "","status":self.status,
                "status_label":self.STATUS_LABELS.get(self.status,self.status),
                "approval_chain_id":self.approval_chain_id,
                "current_step":self.current_step or 0,
                "chain_steps":chain_steps,
                "items":[i.to_dict() for i in self.items],
                "created_at":self.created_at.isoformat()}

class POItem(db.Model):
    __tablename__ = "po_items"
    id          = db.Column(db.Integer, primary_key=True)
    po_id       = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"))
    item_name   = db.Column(db.String(200))
    quantity    = db.Column(db.Float)
    unit_price  = db.Column(db.Float)
    total       = db.Column(db.Float)
    received_qty= db.Column(db.Float, default=0)
    notes       = db.Column(db.Text)
    po = db.relationship("PurchaseOrder", back_populates="items")
    def to_dict(self):
        return {"id":self.id,"po_id":self.po_id,
                "item_name":self.item_name or "","quantity":self.quantity,
                "unit_price":self.unit_price,"total":self.total or 0,
                "received_qty":self.received_qty,"pending_qty":(self.quantity or 0)-(self.received_qty or 0),
                "notes":self.notes or ""}

class GoodsReceipt(db.Model):
    __tablename__ = "goods_receipts"
    id          = db.Column(db.Integer, primary_key=True)
    ref_number  = db.Column(db.String(60), unique=True)
    po_id       = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"))
    warehouse_id= db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    received_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes       = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    po       = db.relationship("PurchaseOrder", back_populates="receipts")
    warehouse= db.relationship("Warehouse")
    supplier = db.relationship("Supplier")
    receiver = db.relationship("User", foreign_keys=[received_by])
    items    = db.relationship("GRNItem", back_populates="grn", cascade="all,delete-orphan")
    def to_dict(self):
        return {"id":self.id,"ref_number":self.ref_number,
                "po_id":self.po_id,
                "po_ref":self.po.ref_number if self.po else "",
                "warehouse_id":self.warehouse_id,
                "warehouse_name":self.warehouse.name if self.warehouse else "",
                "supplier_id":self.supplier_id,
                "supplier_name":self.supplier.name if self.supplier else "",
                "received_by":self.received_by,
                "receiver_name":self.receiver.name if self.receiver else "",
                "notes":self.notes or "",
                "items":[i.to_dict() for i in self.items],
                "created_at":self.created_at.isoformat()}

class GRNItem(db.Model):
    __tablename__ = "grn_items"
    id           = db.Column(db.Integer, primary_key=True)
    grn_id       = db.Column(db.Integer, db.ForeignKey("goods_receipts.id"))
    po_item_id   = db.Column(db.Integer, db.ForeignKey("po_items.id"), nullable=True)
    item_id      = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=True)
    item_name    = db.Column(db.String(200))
    ordered_qty  = db.Column(db.Float)
    received_qty = db.Column(db.Float)
    damaged_qty  = db.Column(db.Float, default=0)
    rejected_qty = db.Column(db.Float, default=0)
    accepted_qty = db.Column(db.Float)
    unit_price   = db.Column(db.Float)
    total        = db.Column(db.Float)
    grn     = db.relationship("GoodsReceipt", back_populates="items")
    po_item = db.relationship("POItem")
    item    = db.relationship("Item")
    def to_dict(self):
        return {"id":self.id,"grn_id":self.grn_id,
                "po_item_id":self.po_item_id,"item_id":self.item_id,
                "item_name":self.item_name or "",
                "ordered_qty":self.ordered_qty,"received_qty":self.received_qty,
                "damaged_qty":self.damaged_qty,"rejected_qty":self.rejected_qty,
                "accepted_qty":self.accepted_qty or 0,
                "unit_price":self.unit_price,"total":self.total or 0}

class PurchaseReturn(db.Model):
    __tablename__ = "purchase_returns"
    id          = db.Column(db.Integer, primary_key=True)
    ref_number  = db.Column(db.String(60), unique=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    warehouse_id= db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    reason      = db.Column(db.String(50))
    notes       = db.Column(db.Text)
    status      = db.Column(db.String(20), default="pending")
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    supplier  = db.relationship("Supplier")
    warehouse = db.relationship("Warehouse")
    items     = db.relationship("PReturnItem", back_populates="preturn", cascade="all,delete-orphan")
    REASON_LABELS = {"damaged":"تالف","wrong_item":"صنف خاطئ","expired":"منتهي الصلاحية","over_supply":"زيادة توريد","other":"أخرى"}
    STATUS_LABELS = {"pending":"قيد المراجعة","approved":"معتمد","returned":"تم الإرجاع","cancelled":"ملغي"}
    def to_dict(self):
        return {"id":self.id,"ref_number":self.ref_number,
                "supplier_id":self.supplier_id,
                "supplier_name":self.supplier.name if self.supplier else "",
                "warehouse_id":self.warehouse_id,
                "warehouse_name":self.warehouse.name if self.warehouse else "",
                "reason":self.reason or "",
                "reason_label":self.REASON_LABELS.get(self.reason,self.reason),
                "notes":self.notes or "","status":self.status,
                "status_label":self.STATUS_LABELS.get(self.status,self.status),
                "items":[i.to_dict() for i in self.items],
                "created_at":self.created_at.isoformat()}

class PReturnItem(db.Model):
    __tablename__ = "preturn_items"
    id           = db.Column(db.Integer, primary_key=True)
    return_id    = db.Column(db.Integer, db.ForeignKey("purchase_returns.id"))
    item_id      = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=True)
    item_name    = db.Column(db.String(200))
    quantity     = db.Column(db.Float)
    unit_price   = db.Column(db.Float)
    total        = db.Column(db.Float)
    reason_detail= db.Column(db.Text)
    preturn = db.relationship("PurchaseReturn", back_populates="items")
    item    = db.relationship("Item")
    def to_dict(self):
        return {"id":self.id,"return_id":self.return_id,
                "item_id":self.item_id,
                "item_name":self.item_name or "",
                "item_code":self.item.code if self.item else "",
                "item_unit":self.item.unit if self.item else "",
                "quantity":self.quantity,"unit_price":self.unit_price,
                "total":self.total or 0,"reason_detail":self.reason_detail or ""}

class SupplierEvaluation(db.Model):
    __tablename__ = "supplier_evaluations"
    id                    = db.Column(db.Integer, primary_key=True)
    supplier_id           = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    po_id                 = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"), nullable=True)
    delivery_accuracy     = db.Column(db.Integer)
    quality_score         = db.Column(db.Integer)
    response_speed        = db.Column(db.Integer)
    price_competitiveness = db.Column(db.Integer)
    notes                 = db.Column(db.Text)
    evaluator_id          = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at            = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    supplier  = db.relationship("Supplier")
    po        = db.relationship("PurchaseOrder")
    evaluator = db.relationship("User", foreign_keys=[evaluator_id])
    @property
    def average_score(self):
        scores = [self.delivery_accuracy, self.quality_score, self.response_speed, self.price_competitiveness]
        valid  = [s for s in scores if s is not None]
        return round(sum(valid)/len(valid), 1) if valid else 0
    def to_dict(self):
        return {"id":self.id,"supplier_id":self.supplier_id,
                "supplier_name":self.supplier.name if self.supplier else "",
                "po_id":self.po_id,
                "po_ref":self.po.ref_number if self.po else "",
                "delivery_accuracy":self.delivery_accuracy,
                "quality_score":self.quality_score,
                "response_speed":self.response_speed,
                "price_competitiveness":self.price_competitiveness,
                "average_score":self.average_score,
                "notes":self.notes or "",
                "evaluator_name":self.evaluator.name if self.evaluator else "",
                "created_at":self.created_at.isoformat()}

class SupplierProfile(db.Model):
    __tablename__ = "supplier_profiles"
    id                    = db.Column(db.Integer, primary_key=True)
    supplier_id           = db.Column(db.Integer, db.ForeignKey("suppliers.id"), unique=True)
    contact_person        = db.Column(db.String(200))
    commercial_register   = db.Column(db.String(100))
    website               = db.Column(db.String(200))
    delivery_accuracy     = db.Column(db.Float, default=0)
    quality_score         = db.Column(db.Float, default=0)
    response_speed        = db.Column(db.Float, default=0)
    price_competitiveness = db.Column(db.Float, default=0)
    total_evaluations     = db.Column(db.Integer, default=0)
    supplier = db.relationship("Supplier")
    def to_dict(self):
        return {"id":self.id,"supplier_id":self.supplier_id,
                "supplier_name":self.supplier.name if self.supplier else "",
                "contact_person":self.contact_person or "",
                "commercial_register":self.commercial_register or "",
                "website":self.website or "",
                "delivery_accuracy":self.delivery_accuracy,
                "quality_score":self.quality_score,
                "response_speed":self.response_speed,
                "price_competitiveness":self.price_competitiveness,
                "total_evaluations":self.total_evaluations}

class InventoryLayer(db.Model):
    __tablename__ = "inventory_layers"
    id          = db.Column(db.Integer, primary_key=True)
    item_id     = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False, index=True)
    warehouse_id= db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    quantity    = db.Column(db.Float, nullable=False, default=0)
    unit_cost   = db.Column(db.Float, nullable=False, default=0)
    ref_type    = db.Column(db.String(30))
    ref_id      = db.Column(db.Integer)
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    item     = db.relationship("Item")
    warehouse= db.relationship("Warehouse")
    def remaining_value(self): return round(self.quantity * self.unit_cost, 2)

    @classmethod
    def add_layer(cls, item_id, warehouse_id, qty, unit_cost, ref_type=None, ref_id=None):
        layer = cls(item_id=item_id, warehouse_id=warehouse_id, quantity=qty, unit_cost=unit_cost, ref_type=ref_type, ref_id=ref_id)
        db.session.add(layer)
        return layer

    @classmethod
    def consume(cls, item_id, warehouse_id, qty):
        layers = cls.query.filter_by(item_id=item_id, warehouse_id=warehouse_id).filter(cls.quantity > 0).order_by(cls.created_at).all()
        remaining = qty
        total_cost = 0.0
        for layer in layers:
            if remaining <= 0: break
            take = min(layer.quantity, remaining)
            layer.quantity -= take
            remaining -= take
            total_cost += take * layer.unit_cost
        return total_cost, qty - remaining  # (total_cost, actually_consumed)

    @classmethod
    def get_valuation(cls, item_id, warehouse_id=None):
        q = cls.query.filter(cls.quantity > 0)
        if warehouse_id: q = q.filter_by(warehouse_id=warehouse_id)
        q = q.filter_by(item_id=item_id)
        total_qty = db.session.query(func.sum(cls.quantity)).filter(cls.item_id == item_id).scalar() or 0
        total_val = db.session.query(func.sum(cls.quantity * cls.unit_cost)).filter(cls.item_id == item_id).scalar() or 0
        avg_cost = round(total_val / total_qty, 2) if total_qty > 0 else 0
        return {"item_id": item_id, "total_qty": total_qty, "total_value": round(total_val, 2), "avg_cost": avg_cost, "layers": [l.to_dict() for l in q.all()]}

    def to_dict(self):
        return {"id": self.id, "item_id": self.item_id, "item_name": self.item.name if self.item else "",
                "warehouse_id": self.warehouse_id, "quantity": self.quantity, "unit_cost": self.unit_cost,
                "remaining_value": self.remaining_value(), "ref_type": self.ref_type, "ref_id": self.ref_id,
                "created_at": self.created_at.isoformat()}

    @classmethod
    def cleanup_layers(cls):
        return cls.query.filter(cls.quantity == 0).delete()


class Lot(db.Model):
    __tablename__ = "lots"
    id          = db.Column(db.Integer, primary_key=True)
    item_id     = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False, index=True)
    lot_number  = db.Column(db.String(100), nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=True)
    status      = db.Column(db.String(20), default="active")
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    item        = db.relationship("Item")
    __table_args__ = (db.UniqueConstraint("item_id", "lot_number", name="uq_lot"),)
    def to_dict(self):
        return {"id":self.id,"item_id":self.item_id,"item_name":self.item.name if self.item else "",
                "lot_number":self.lot_number,
                "expiry_date":self.expiry_date.strftime("%Y-%m-%d") if self.expiry_date else None,
                "status":self.status,
                "created_at":self.created_at.isoformat() if self.created_at else ""}


class UnitConversion(db.Model):
    __tablename__ = "unit_conversions"
    id        = db.Column(db.Integer, primary_key=True)
    from_unit = db.Column(db.String(30), nullable=False)
    to_unit   = db.Column(db.String(30), nullable=False)
    factor    = db.Column(db.Float, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint("from_unit", "to_unit", name="uq_conv"),)
    def to_dict(self):
        return {"id":self.id,"from_unit":self.from_unit,"to_unit":self.to_unit,"factor":self.factor}


class ApprovalChain(db.Model):
    __tablename__ = "approval_chains"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(30), nullable=False)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    steps       = db.relationship("ApprovalStep", backref="chain", lazy="joined", order_by="ApprovalStep.step_order",
                                  cascade="all, delete-orphan")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"target_type":self.target_type,
                "is_active":self.is_active,"steps":[s.to_dict() for s in self.steps]}


class ApprovalStep(db.Model):
    __tablename__ = "approval_steps"
    id          = db.Column(db.Integer, primary_key=True)
    chain_id    = db.Column(db.Integer, db.ForeignKey("approval_chains.id"), nullable=False)
    step_order  = db.Column(db.Integer, nullable=False)
    role        = db.Column(db.String(30), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approval_type = db.Column(db.String(10), default="any")
    user        = db.relationship("User")
    def to_dict(self):
        return {"id":self.id,"chain_id":self.chain_id,"step_order":self.step_order,
                "role":self.role,"user_id":self.user_id,"approval_type":self.approval_type}
