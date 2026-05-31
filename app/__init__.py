"""Flask Application Factory"""
import os, socket, datetime, shutil
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO, emit, join_room
from app.limiter import limiter
from app.models import (db, User, Warehouse, Category, Supplier,
                         Item, Stock, StockMovement, Transfer,
                         InventoryCount, InventoryCountLine, Project,
                         BackupConfig,
                         PurchaseRequest, PRItem, ApprovalLog,
                         RFQ, RFQSupplier, Quotation, QuotationItem,
                         PurchaseOrder, POItem,
                         GoodsReceipt, GRNItem,
                         PurchaseReturn, PReturnItem,
                         SupplierEvaluation, SupplierProfile)
from app.middleware import register_jwt_callbacks, register_request_hooks, register_error_handlers
from app.routes import api

socketio = SocketIO()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def create_app(cfg=None):
    app = Flask(__name__)
    if cfg is None:
        from config import get_config
        cfg = get_config()
    app.config.from_object(cfg)

    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins":"*"}},
         allow_headers=["Content-Type","Authorization"],
         methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
         supports_credentials=True)

    socketio.init_app(app, cors_allowed_origins="*")

    limiter.init_app(app)

    register_jwt_callbacks(jwt)
    register_request_hooks(app)
    register_error_handlers(app)

    from flasgger import Swagger
    Swagger(app, template={
        "swagger": "2.0",
        "info": {"title": "Alnubala WMS API", "version": "2.0.0", "description": "نظام إدارة المخازن والمشتريات"},
        "basePath": "/api",
        "securityDefinitions": {"Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}},
    })

    app.register_blueprint(api)

    @socketio.on("connect")
    def ws_connect():
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        try:
            verify_jwt_in_request(optional=True)
            uid = get_jwt_identity()
            if uid:
                join_room(f"user_{uid}")
        except:
            pass

    @app.route("/health")
    def health():
        return jsonify({"status":"ok","version":"2.0",
                        "time":datetime.datetime.utcnow().isoformat(),
                        "local_ip":get_local_ip()})

    @app.route("/")
    def index():
        import os as _os
        _dir = _os.path.dirname(_os.path.abspath(__file__))
        _root = _os.path.dirname(_dir)
        resp = send_from_directory(_root, "index.html")
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/manifest.json")
    def manifest():
        return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "..", "manifest.json")
    @app.route("/sw.js")
    def sw():
        return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "..", "sw.js")

    with app.app_context():
        os.makedirs(app.config.get("UPLOAD_FOLDER","uploads"), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","backups"), exist_ok=True)
        db.create_all()
        _migrate(db)
        _seed(app)
    _init_scheduler(app)
    return app

def get_socketio():
    return socketio

def _init_scheduler(app):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        sched = BackgroundScheduler(daemon=True)
        def auto_backup_job():
            with app.app_context():
                try:
                    enabled = BackupConfig.query.filter_by(key="auto_backup_enabled").first()
                    if not enabled or enabled.value != "true": return
                    db_path = app.config.get("SQLALCHEMY_DATABASE_URI","").replace("sqlite:///","")
                    if not os.path.isabs(db_path):
                        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..",db_path)
                    if not os.path.exists(db_path): return
                    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","backups")
                    os.makedirs(backup_dir, exist_ok=True)
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_name = f"wms_auto_backup_{ts}.db"
                    shutil.copy2(db_path, os.path.join(backup_dir, backup_name))
                    keep = int((BackupConfig.query.filter_by(key="backup_keep_count").first() or BackupConfig(key="backup_keep_count",value="10")).value)
                    all_b = sorted([f for f in os.listdir(backup_dir) if f.startswith("wms_auto_backup_")], reverse=True)
                    for old in all_b[keep:]:
                        try: os.remove(os.path.join(backup_dir,old))
                        except: pass
                    c = BackupConfig.query.filter_by(key="last_backup").first()
                    if c: c.value = ts
                    db.session.commit()
                except: pass
        interval = int((app.config.get("BACKUP_INTERVAL_HOURS",24))) * 3600
        sched.add_job(auto_backup_job, "interval", seconds=interval, id="auto_backup", replace_existing=True)
        sched.start()
    except ImportError:
        app.logger.warning("APScheduler not installed — auto backup disabled")
    except Exception as e:
        app.logger.warning(f"Backup scheduler init failed: {e}")


def _column_exists(table, col):
    try:
        return any(r[1]==col for r in db.session.execute(db.text(f"PRAGMA table_info({table})")))
    except: return False

def _add_col(table, col, dtype):
    if not _column_exists(table, col):
        try:
            db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}"))
            db.session.commit()
        except: db.session.rollback()

def _migrate(db):
    _add_col("projects","actual_cost","FLOAT DEFAULT 0.0")
    _add_col("projects","completion_pct","FLOAT DEFAULT 0.0")
    _add_col("purchase_orders","total_amount","FLOAT DEFAULT 0.0")
    if not _column_exists("project_invoices","ref_number"):
        db.create_all()

def _seed(app):
    if User.query.count() > 0: return
    app.logger.info("🌱 Seeding initial data...")
    wh1=Warehouse(name="المخزن الرئيسي",code="WH-MAIN",location="المستودع الرئيسي",capacity=1000,type="main")
    wh2=Warehouse(name="الفرع الأول",   code="WH-S1",  location="موقع المشروع A",  capacity=500, type="sub")
    wh3=Warehouse(name="الفرع الثاني",  code="WH-S2",  location="موقع المشروع B",  capacity=400, type="sub")
    db.session.add_all([wh1,wh2,wh3]); db.session.flush()
    cats={}
    for n,c,i in [("حديد وصلب","#E74C3C","⚙️"),("مواد بناء","#8E44AD","🧱"),
                  ("تشطيبات","#3498DB","🎨"),("سباكة","#1ABC9C","🔧"),
                  ("خشب","#D35400","🪵"),("دهانات","#F1C40F","🖌️"),
                  ("ركام","#95A5A6","⛏️"),("كهرباء","#2ECC71","⚡")]:
        obj=Category(name=n,color=c,icon=i); db.session.add(obj); db.session.flush(); cats[n]=obj
    for idx,(nm,cat,ph,rt) in enumerate([
        ("شركة الحديد السعودية","حديد وصلب","0500-111-222",5),
        ("مصنع النيل للأسمنت","مواد بناء","0500-333-444",4),
        ("شركة الخليج للتشطيبات","تشطيبات","0500-555-666",3),
        ("مؤسسة المياه للسباكة","سباكة","0500-777-888",4)],1):
        db.session.add(Supplier(code=f"SUP-{idx:02d}",name=nm,category=cat,phone=ph,rating=rt))
    users={}
    for nm,un,em,pw,rl,wid in [
        ("أحمد المدير","admin","admin@wh.com","admin123","admin",None),
        ("محمد علي","keeper1","k1@wh.com","keeper123","keeper",wh1.id),
        ("خالد أحمد","keeper2","k2@wh.com","keeper123","keeper",wh2.id),
        ("سالم عبد","keeper3","k3@wh.com","keeper123","keeper",wh3.id),
        ("فاطمة الحسن","viewer","v@wh.com","viewer123","viewer",None)]:
        u=User(name=nm,username=un,email=em,role=rl,warehouse_id=wid)
        u.set_password(pw); db.session.add(u); db.session.flush(); users[un]=u
    adm=users["admin"]; now=datetime.datetime.utcnow()
    items_data=[
        ("WH-0001","BAR0001","حديد تسليح Ø16","حديد وصلب","طن",  20,25,2500,{wh1.id:12,wh2.id:5, wh3.id:0}),
        ("WH-0002","BAR0002","أسمنت CEM I",   "مواد بناء","كيس", 100,120,25,{wh1.id:40,wh2.id:20,wh3.id:15}),
        ("WH-0003","BAR0003","حديد تسليح Ø12","حديد وصلب","طن",  50,60,2300, {wh1.id:85,wh2.id:30,wh3.id:12}),
        ("WH-0004","BAR0004","سيراميك 60×60", "تشطيبات",  "م²", 500,600,45, {wh1.id:1200,wh2.id:300,wh3.id:800}),
        ("WH-0005","BAR0005",'مواسير PVC 4"', "سباكة",    "م",  200,250,18, {wh1.id:0,  wh2.id:500,wh3.id:150}),
        ("WH-0006","BAR0006","رمل خشن",       "ركام",     "م³", 200,250,35, {wh1.id:450,wh2.id:80, wh3.id:120}),
        ("WH-0007","BAR0007","خشب تفصيل 2×4","خشب",      "قطعة",250,300,12,{wh1.id:200,wh2.id:80, wh3.id:60}),
        ("WH-0008","BAR0008","دهان أكريليك",  "دهانات",   "لتر", 100,120,28,{wh1.id:320,wh2.id:120,wh3.id:90}),
        ("WH-0009","BAR0009","بلاط 40×40",    "تشطيبات",  "م²", 300,350,38,{wh1.id:600,wh2.id:200,wh3.id:100}),
        ("WH-0010","BAR0010","أسلاك كهربائية","كهرباء",   "م",  1000,1200,8,{wh1.id:2000,wh2.id:500,wh3.id:300}),
        ("WH-0011","BAR0011","طوب مفرغ",      "مواد بناء","قطعة",2000,2500,2.5,{wh1.id:5000,wh2.id:1000,wh3.id:2000}),
        ("WH-0012","BAR0012","شبك رابيتز",    "حديد وصلب","رول",40,50,85,  {wh1.id:80, wh2.id:20, wh3.id:30}),
    ]
    for code,bc,name,cat,unit,mn,ro,pr,stk in items_data:
        itm=Item(code=code,barcode=bc,name=name,category_id=cats[cat].id,
                 unit=unit,min_quantity=mn,reorder_point=ro,unit_price=pr)
        db.session.add(itm); db.session.flush()
        for wid,qty in stk.items():
            db.session.add(Stock(item_id=itm.id,warehouse_id=wid,quantity=qty))
            if qty>0:
                db.session.add(StockMovement(
                    ref_number=f"SEED-{code}-{wid}",type="in",
                    item_id=itm.id,warehouse_id=wid,quantity=qty,unit_price=pr,
                    user_id=adm.id,notes="رصيد أولي",
                    created_at=now-datetime.timedelta(days=3)))
    i1=Item.query.filter_by(code="WH-0001").first()
    i2=Item.query.filter_by(code="WH-0002").first()
    i4=Item.query.filter_by(code="WH-0004").first()
    k2=users["keeper2"]; k3=users["keeper3"]
    for idx,(itm,fw,tw,qty,rsn,st,rby,da) in enumerate([
        (i1,wh1.id,wh2.id,8,"احتياج موقع A","pending",k2.id,0),
        (i2,wh1.id,wh3.id,50,"احتياج موقع B","pending",k3.id,0),
        (i4,wh1.id,wh3.id,200,"بدء التشطيبات","executed",k3.id,2)],1):
        if itm:
            db.session.add(Transfer(
                ref_number=f"TR-{88+idx:03d}",item_id=itm.id,
                from_warehouse_id=fw,to_warehouse_id=tw,quantity=qty,
                reason=rsn,status=st,requested_by=rby,
                approved_by=adm.id if st=="executed" else None,
                approved_at=now if st=="executed" else None,
                created_at=now-datetime.timedelta(days=da)))
    db.session.commit()
    app.logger.info("✅ Seed complete.")
