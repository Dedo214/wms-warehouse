"""Comprehensive demo data seeder for Alnubala WMS"""
import datetime, random
from app.models import (db, User, Warehouse, Category, Supplier, Item, Stock,
    StockMovement, InventoryLayer, Notification, Lot, ScheduledCount,
    Transfer, PurchaseOrder, POItem, GoodsReceipt, GRNItem, Project,
    ProjectInvoice, SaleOrder, SaleItem, PurchaseReturn, PReturnItem)

def rng(a, b): return round(random.uniform(a, b), 2)
def ref(prefix):
    import datetime as _dt
    return f"{prefix}-{_dt.datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
def days_ago(n): return datetime.datetime.utcnow() - datetime.timedelta(days=n)
def date_ago(n): return days_ago(n).date()

def seed_all(force=False):
    """Seed the database with comprehensive demo data.
    If force=True, clears existing data first."""
    if not force and User.query.count() > 1:
        return {"ok": False, "msg": "البيانات موجودة مسبقاً. استخدم force لإعادة الإنشاء"}

    if force:
        # Clear data in reverse dependency order
        for t in [SaleItem, SaleOrder, PReturnItem, PurchaseReturn, GRNItem, GoodsReceipt,
                  POItem, PurchaseOrder, InventoryLayer, StockMovement, Transfer,
                  Notification, Lot, InventoryLayer, Stock, Item, Supplier,
                  ProjectInvoice, Project, User, Category, Warehouse]:
            t.query.delete()
        db.session.commit()

    # ── 1. WAREHOUSES ──
    wh_data = [
        ("المستودع الرئيسي - الرياض", "WH-MAIN", "الرياض - المنطقة الصناعية", 50000, "main"),
        ("مستودع مشروع النخيل", "WH-PALM", "الخرج - حي النخيل", 15000, "sub"),
        ("مستودع أبراج البحر", "WH-SEA", "جدة - الكورنيش", 20000, "sub"),
        ("مستودع المواد الكيماوية", "WH-CHEM", "الدمام - الصناعية الثانية", 10000, "sub"),
    ]
    for nm, cd, loc, cap, tp in wh_data:
        db.session.add(Warehouse(name=nm, code=cd, location=loc, capacity=cap, type=tp))
    db.session.commit()
    whs = {w.code: w for w in Warehouse.query.all()}

    # ── 2. CATEGORIES ──
    cat_data = [
        ("حديد تسليح", "🔩", "#E74C3C"), ("أسمنت وخرسانة", "🧱", "#7F8C8D"),
        ("مواد كهربائية", "⚡", "#F39C12"), ("مواد صحية", "🚿", "#3498DB"),
        ("دهانات وعوازل", "🎨", "#9B59B6"), ("أخشاب ونجارة", "🪵", "#795548"),
        ("مواد سباكة", "🔧", "#1ABC9C"), ("أدوات أمان", "🪖", "#E67E22"),
        ("مواد تشطيب", "🏠", "#2ECC71"), ("عدد يدوية", "🛠️", "#34495E"),
    ]
    cats = {}
    for nm, ic, co in cat_data:
        c = Category(name=nm, icon=ic, color=co)
        db.session.add(c); cats[nm] = c
    db.session.commit()

    # ── 3. ITEMS ──
    items_data = [
        ("حديد تسليح 8 مم", "REBAR-8", "6281001001010", "حديد تسليح", "طن", 10, 15, 2800),
        ("حديد تسليح 12 مم", "REBAR-12", "6281001001027", "حديد تسليح", "طن", 8, 12, 2750),
        ("حديد تسليح 16 مم", "REBAR-16", "6281001001034", "حديد تسليح", "طن", 5, 8, 2700),
        ("حديد تسليح 20 مم", "REBAR-20", "6281001001041", "حديد تسليح", "طن", 3, 5, 2650),
        ("أسمنت بورتلاند 50 كجم", "CEM-50", "6281002001018", "أسمنت وخرسانة", "كيس", 200, 300, 18),
        ("أسمنت مقاوم 50 كجم", "CEM-RES", "6281002001025", "أسمنت وخرسانة", "كيس", 100, 150, 22),
        ("خرسانة جاهزة C30", "CONC-C30", "6281002001032", "أسمنت وخرسانة", "م³", 20, 30, 320),
        ("سلك نحاس 4 مم", "WIRE-4", "6281003001016", "مواد كهربائية", "متر", 500, 1000, 2.5),
        ("سلك نحاس 6 مم", "WIRE-6", "6281003001023", "مواد كهربائية", "متر", 300, 600, 3.8),
        ("مفتاح كهربائي 16 أمبير", "SW-16A", "6281003001030", "مواد كهربائية", "قطعة", 100, 200, 12),
        ("قاطع كهربائي 32 أمبير", "BRK-32A", "6281003001047", "مواد كهربائية", "قطعة", 80, 150, 45),
        ("كابل طاقة 3×4 مم", "CBL-3X4", "6281003001054", "مواد كهربائية", "متر", 200, 400, 18),
        ("خلاط ماء (حنفية)", "FAUCET", "6281004001014", "مواد صحية", "قطعة", 30, 50, 85),
        ("مواسير صحي 2 بوصة", "PIPE-2", "6281004001021", "مواد صحية", "متر", 60, 100, 35),
        ("صمام ماء نحاس", "VALVE-CU", "6281004001038", "مواد صحية", "قطعة", 25, 40, 120),
        ("دهان زيتي أبيض 4ل", "OIL-WHITE", "6281005001012", "دهانات وعوازل", "علبة", 40, 60, 145),
        ("معجون جدران 20كجم", "PUTTY-20", "6281005001029", "دهانات وعوازل", "كيس", 30, 50, 38),
        ("عازل مائي (بيتومين)", "BITUMEN", "6281005001036", "دهانات وعوازل", "برميل", 10, 15, 680),
        ("خشب كونتر 18 مم", "PLY-18", "6281006001010", "أخشاب ونجارة", "لوح", 80, 120, 95),
        ("خشب موسكي 2×4", "TIMB-2X4", "6281006001027", "أخشاب ونجارة", "متر طولي", 400, 600, 8),
        ("مثقاب كهربائي 650 واط", "DRILL-650", "6281007001018", "عدد يدوية", "قطعة", 5, 8, 320),
        ("شريط قياس 5 متر", "TAPE-5M", "6281007001025", "عدد يدوية", "قطعة", 20, 30, 25),
        ("ميزان ليزر", "LASER-LVL", "6281007001032", "عدد يدوية", "قطعة", 3, 5, 950),
        ("خوذة أمان", "HELMET", "6281008001016", "أدوات أمان", "قطعة", 50, 80, 35),
        ("حزام أمان", "HARNESS", "6281008001023", "أدوات أمان", "قطعة", 15, 25, 280),
        ("قفازات عمل", "GLOVES", "6281008001030", "أدوات أمان", "زوج", 100, 150, 12),
        ("بلاط سيراميك 40×40", "TILE-40X40", "6281009001014", "مواد تشطيب", "م²", 200, 300, 45),
        ("بلاط رخام 60×60", "MARBLE-60X60", "6281009001021", "مواد تشطيب", "م²", 50, 80, 185),
        ("أرضيات خشب LVT", "LVT-FLOOR", "6281009001038", "مواد تشطيب", "م²", 80, 120, 120),
        ("مواسير PVC 4 بوصة", "PVC-4", "6281010001012", "مواد سباكة", "متر", 100, 150, 25),
        ("مواسير PVC 6 بوصة", "PVC-6", "6281010001029", "مواد سباكة", "متر", 60, 100, 38),
        ("كوع PVC 4 بوصة", "ELBOW-4", "6281010001036", "مواد سباكة", "قطعة", 80, 120, 8),
    ]
    items_list = []
    for nm, cd, bc, cat_nm, unt, mn, rop, pr in items_data:
        it = Item(code=cd, barcode=bc, name=nm, category_id=cats[cat_nm].id,
                  unit=unt, min_quantity=mn, reorder_point=rop, unit_price=pr)
        db.session.add(it); items_list.append(it)
    db.session.commit()

    # ── 4. SUPPLIERS ──
    sup_data = [
        ("SUP-RIYADH-STEEL", "شركة الرياض للحديد والصلب", "حديد", "0112345678", "info@riyadhsteel.com", "الرياض", "310123456789", "30 يوم"),
        ("SUP-SAUDI-CEMENT", "الشركة السعودية للأسمنت", "أسمنت", "0123456789", "info@saudicement.com", "الهفوف", "310987654321", "نقداً"),
        ("SUP-ELEC-GULF", "شركة الخليج للمواد الكهربائية", "كهرباء", "0134567890", "sales@gulfelec.com", "الدمام", "310456789123", "30 يوم"),
        ("SUP-PLUMB-KING", "مؤسسة ملك السباكة", "مواد صحية", "0145678901", "info@plumbingking.com", "جدة", "310321654987", "15 يوم"),
        ("SUP-PAINT-CO", "شركة الدهانات العربية", "دهانات", "0156789012", "info@arabianpaints.com", "الرياض", "310654321789", "نقداً"),
        ("SUP-WOOD-WORLD", "مؤسسة عالم الأخشاب", "أخشاب", "0167890123", "info@woodworld.com", "الدمام", "310789123456", "30 يوم"),
        ("SUP-SAFETY-FIRST", "شركة السلامة أولاً", "أمان", "0178901234", "info@safetyfirst.com", "جدة", "310456789012", "20 يوم"),
        ("SUP-MARBLE-CO", "مؤسسة الرخام السعودي", "تشطيب", "0189012345", "info@saudimarble.com", "الرياض", "310789456123", "30 يوم"),
    ]
    supps = []
    for cd, nm, cat, ph, em, addr, tax, pt in sup_data:
        s = Supplier(code=cd, name=nm, category=cat, phone=ph, email=em, address=addr, tax_number=tax, payment_terms=pt, rating=random.randint(3, 5))
        db.session.add(s); supps.append(s)
    db.session.commit()

    # ── 5. USERS ──
    user_data = [
        ("مشرف النظام", "admin", "admin@alnubala.com", "admin123", "super_admin", None),
        ("أمين المستودع", "keeper1", "keeper@alnubala.com", "keeper123", "keeper", whs["WH-MAIN"].id),
        ("مشرف المشتريات", "purch1", "purch@alnubala.com", "purch123", "purchasing", None),
        ("مدير المبيعات", "sales1", "sales@alnubala.com", "sales123", "manager", None),
        ("مشرف المخازن", "manager1", "mgr@alnubala.com", "mgr123", "manager", None),
    ]
    usr_map = {}
    for nm, un, em, pw, rl, wid in user_data:
        u = User(name=nm, username=un, email=em, role=rl, warehouse_id=wid)
        u.set_password(pw); db.session.add(u); usr_map[un] = u
    db.session.commit()

    # ── 6. PROJECTS ──
    proj_data = [
        ("مشروع النخيل السكني", "PROJ-PALM", "200 فيلا سكنية", "شركة النخيل العقارية", "الخرج", 50000000, 32000000, 65),
        ("أبراج البحر التجارية", "PROJ-SEA", "3 أبراج تجارية", "شركة البحر للتطوير", "جدة الكورنيش", 120000000, 45000000, 38),
        ("مستودع المنطقة الصناعية", "PROJ-IND", "مستودع 5000 م²", "النبلاء للمقاولات", "الرياض", 8000000, 1500000, 20),
        ("تطوير طريق الملك", "PROJ-KING", "بنية تحتية 15 كم", "أمانة الرياض", 75000000, 28000000, 42),
        ("برج المملكة الطبي", "PROJ-MED", "برج طبي 12 دور", "مجموعة المملكة الطبية", "الرياض", 90000000, 10000000, 12),
    ]
    projs = []
    for nm, cd, desc, clnt, loc, budg, act, pct in proj_data:
        p = Project(name=nm, code=cd, description=desc, client=clnt, location=loc, budget=budg, actual_cost=act, completion_pct=pct, status="active", start_date=date_ago(180), end_date=date_ago(-365))
        db.session.add(p); projs.append(p)
    db.session.commit()

    # ── 7. STOCK ──
    stock_plan = {
        "REBAR-8": (35, whs["WH-MAIN"].id, 2700), "REBAR-12": (25, whs["WH-MAIN"].id, 2650),
        "REBAR-16": (18, whs["WH-MAIN"].id, 2600), "REBAR-20": (12, whs["WH-MAIN"].id, 2550),
        "CEM-50": (800, whs["WH-MAIN"].id, 17), "CEM-RES": (400, whs["WH-MAIN"].id, 21),
        "CONC-C30": (80, whs["WH-MAIN"].id, 310),
        "WIRE-4": (2500, whs["WH-MAIN"].id, 2.3), "WIRE-6": (1500, whs["WH-MAIN"].id, 3.5),
        "SW-16A": (600, whs["WH-MAIN"].id, 10), "BRK-32A": (400, whs["WH-MAIN"].id, 40),
        "CBL-3X4": (1000, whs["WH-MAIN"].id, 16),
        "FAUCET": (120, whs["WH-MAIN"].id, 75), "PIPE-2": (250, whs["WH-MAIN"].id, 30),
        "VALVE-CU": (80, whs["WH-MAIN"].id, 110),
        "OIL-WHITE": (200, whs["WH-MAIN"].id, 135), "PUTTY-20": (120, whs["WH-MAIN"].id, 35),
        "BITUMEN": (40, whs["WH-MAIN"].id, 650),
        "PLY-18": (300, whs["WH-MAIN"].id, 85), "TIMB-2X4": (2000, whs["WH-MAIN"].id, 7),
        "DRILL-650": (20, whs["WH-MAIN"].id, 300), "TAPE-5M": (80, whs["WH-MAIN"].id, 22),
        "LASER-LVL": (8, whs["WH-MAIN"].id, 900),
        "HELMET": (200, whs["WH-MAIN"].id, 30), "HARNESS": (40, whs["WH-MAIN"].id, 250),
        "GLOVES": (400, whs["WH-MAIN"].id, 10),
        "TILE-40X40": (600, whs["WH-MAIN"].id, 42), "MARBLE-60X60": (120, whs["WH-MAIN"].id, 175),
        "LVT-FLOOR": (300, whs["WH-MAIN"].id, 110),
        "PVC-4": (500, whs["WH-MAIN"].id, 22), "PVC-6": (250, whs["WH-MAIN"].id, 35),
        "ELBOW-4": (400, whs["WH-MAIN"].id, 7),
        "REBAR-12": (8, whs["WH-PALM"].id, 2680), "REBAR-16": (5, whs["WH-PALM"].id, 2620),
        "CEM-50": (150, whs["WH-PALM"].id, 18), "CEM-RES": (80, whs["WH-PALM"].id, 22),
        "WIRE-4": (400, whs["WH-PALM"].id, 2.5), "WIRE-6": (200, whs["WH-PALM"].id, 3.8),
        "PVC-4": (100, whs["WH-PALM"].id, 25), "ELBOW-4": (80, whs["WH-PALM"].id, 8),
        "TILE-40X40": (200, whs["WH-PALM"].id, 45), "OIL-WHITE": (30, whs["WH-PALM"].id, 140),
        "HELMET": (30, whs["WH-PALM"].id, 32), "GLOVES": (60, whs["WH-PALM"].id, 11),
        "REBAR-16": (10, whs["WH-SEA"].id, 2620), "CEM-50": (200, whs["WH-SEA"].id, 18),
        "CEM-RES": (60, whs["WH-SEA"].id, 22), "CONC-C30": (30, whs["WH-SEA"].id, 315),
        "CBL-3X4": (300, whs["WH-SEA"].id, 17), "BRK-32A": (100, whs["WH-SEA"].id, 42),
        "MARBLE-60X60": (400, whs["WH-SEA"].id, 180), "LVT-FLOOR": (150, whs["WH-SEA"].id, 115),
        "VALVE-CU": (30, whs["WH-SEA"].id, 115), "PVC-6": (80, whs["WH-SEA"].id, 36),
        "BITUMEN": (15, whs["WH-SEA"].id, 660), "HARNESS": (12, whs["WH-SEA"].id, 260),
    }
    adm = usr_map["admin"]
    for code, (qty, wh_id, cost) in stock_plan.items():
        it = Item.query.filter_by(code=code).first()
        if not it: continue
        s = Stock.get_or_create(it.id, wh_id)
        s.quantity = max(0, s.quantity + qty)
        if qty > 0:
            InventoryLayer.add_layer(it.id, wh_id, qty, cost, ref_type="seed")
    db.session.commit()

    # ── 8. HISTORICAL MOVEMENTS ──
    keeper = usr_map["keeper1"]; purch_user = usr_map["purch1"]
    sales_user = usr_map["sales1"]
    mov_templates = [
        ("CEM-50", "WH-MAIN", "in", (100, 400), 0.7), ("REBAR-12", "WH-MAIN", "in", (5, 20), 0.5),
        ("WIRE-4", "WH-MAIN", "in", (200, 600), 0.6), ("PVC-4", "WH-MAIN", "in", (50, 200), 0.4),
        ("TILE-40X40", "WH-MAIN", "in", (100, 300), 0.5), ("OIL-WHITE", "WH-MAIN", "in", (30, 80), 0.4),
        ("HELMET", "WH-MAIN", "in", (30, 100), 0.3), ("DRILL-650", "WH-MAIN", "in", (2, 8), 0.2),
        ("CEM-50", "WH-MAIN", "out", (50, 200), 0.6), ("REBAR-12", "WH-MAIN", "out", (3, 10), 0.5),
        ("REBAR-16", "WH-MAIN", "out", (2, 8), 0.4), ("WIRE-4", "WH-MAIN", "out", (100, 400), 0.5),
        ("WIRE-6", "WH-MAIN", "out", (50, 200), 0.4), ("PLY-18", "WH-MAIN", "out", (20, 80), 0.4),
        ("TILE-40X40", "WH-MAIN", "out", (50, 200), 0.4), ("PVC-4", "WH-MAIN", "out", (20, 100), 0.3),
        ("OIL-WHITE", "WH-MAIN", "out", (10, 40), 0.3), ("GLOVES", "WH-MAIN", "out", (20, 80), 0.3),
    ]
    mov_count = 0
    for _ in range(120):
        if random.random() > 0.7: continue
        tmpl = random.choice(mov_templates)
        item_code, wh_code, tp, (qmin, qmax), prob = tmpl
        if random.random() > prob: continue
        it = Item.query.filter_by(code=item_code).first()
        wh = whs.get(wh_code)
        if not it or not wh: continue
        dt = days_ago(random.randint(1, 180))
        qty = rng(qmin, qmax)
        proj = random.choice(["مشروع النخيل", "أبراج البحر", "تطوير طريق الملك", "برج المملكة الطبي", None])
        m = StockMovement(ref_number=ref("MOV"), type=tp, item_id=it.id, warehouse_id=wh.id,
                          quantity=qty, unit_price=it.unit_price,
                          supplier_id=random.choice(supps).id if tp == "in" else None,
                          user_id=keeper.id if tp == "out" else purch_user.id,
                          notes=f"حركة {'وارد' if tp=='in' else 'صرف'} (بيانات تجريبية)",
                          project=proj, created_at=dt)
        db.session.add(m)
        s = Stock.get_or_create(it.id, wh.id)
        if tp == "in":
            s.quantity += qty
            InventoryLayer.add_layer(it.id, wh.id, qty, it.unit_price, ref_type="movement", ref_id=m.id)
        else:
            taken = min(qty, s.quantity)
            InventoryLayer.consume(it.id, wh.id, taken)
            s.quantity -= taken
        mov_count += 1
    db.session.commit()

    # ── 9. TRANSFERS ──
    for _ in range(8):
        it = random.choice(items_list)
        qty = rng(5, 50)
        fw, tw = random.sample(list(whs.values()), 2)
        if fw.id == tw.id: continue
        st = Stock.get_or_create(it.id, fw.id)
        if st.quantity < qty: continue
        st.quantity -= qty; InventoryLayer.consume(it.id, fw.id, qty)
        ts = Stock.get_or_create(it.id, tw.id); ts.quantity += qty
        InventoryLayer.add_layer(it.id, tw.id, qty, it.unit_price, ref_type="transfer")
        db.session.add(Transfer(ref_number=ref("TRF"), item_id=it.id, from_warehouse_id=fw.id,
            to_warehouse_id=tw.id, quantity=qty,
            reason=random.choice(["نقل لمشروع", "إعادة توزيع", "تغذية مخزن فرعي"]),
            status=random.choice(["executed", "executed", "executed", "pending"]),
            requested_by=keeper.id, approved_by=adm.id if random.random() > 0.3 else None,
            created_at=days_ago(random.randint(5, 90))))
    db.session.commit()

    # ── 10. PURCHASE ORDERS + GRNs ──
    sup_list = Supplier.query.all()
    for i in range(6):
        sup = random.choice(sup_list); dt = date_ago(random.randint(10, 120))
        po = PurchaseOrder(ref_number=ref("PO"), supplier_id=sup.id,
            warehouse_id=random.choice(list(whs.values())).id,
            project_id=random.choice(projs).id if random.random() > 0.5 else None,
            total_amount=0, order_date=dt, currency="SAR",
            payment_terms=random.choice(["نقداً", "30 يوم", "60 يوم"]),
            status=random.choice(["draft", "approved", "completed", "completed"]),
            created_by=purch_user.id)
        po_total = 0
        for _ in range(random.randint(2, 4)):
            it = random.choice(items_list)
            qty = rng(5, 100); up = it.unit_price * rng(0.85, 1.05); total = qty * up
            po_total += total
            po.items.append(POItem(item_name=it.name, quantity=qty, unit_price=round(up, 2),
                                    total=round(total, 2),
                                    received_qty=round(qty * 0.9, 2) if po.status == "completed" else 0))
        po.total_amount = round(po_total, 2)
        db.session.add(po)
        if po.status == "completed":
            grn = GoodsReceipt(ref_number=ref("GRN"), po_id=po.id, warehouse_id=po.warehouse_id,
                supplier_id=sup.id, received_by=keeper.id, notes="إستلام كامل", created_at=days_ago(7))
            for pi in po.items:
                acc = round(pi.quantity * 0.95, 2)
                grn.items.append(GRNItem(item_name=pi.item_name, ordered_qty=pi.quantity,
                    received_qty=acc, damaged_qty=round(pi.quantity * 0.03, 2),
                    rejected_qty=round(pi.quantity * 0.02, 2), accepted_qty=acc,
                    unit_price=pi.unit_price, total=round(acc * pi.unit_price, 2)))
            db.session.add(grn)
    db.session.commit()

    # ── 11. SALES ORDERS ──
    for _ in range(15):
        c = random.choice([
            ("شركة البناء الحديث", "0501234567"), ("مؤسسة الإنشاءات المتقدمة", "0552345678"),
            ("شركة الخليج للتطوير", "0563456789"), ("مقاول أحمد الحربي", "0504567890"),
            ("شركة العمران القابضة", "0585678901"), ("مؤسسة الجبر للمقاولات", "0596789012"),
        ])
        so = SaleOrder(ref_number=ref("SO"), customer_name=c[0], customer_phone=c[1],
            sale_date=date_ago(random.randint(1, 90)),
            warehouse_id=random.choice(list(whs.values())).id,
            discount_pct=rng(0, 5), tax_pct=15,
            status=random.choice(["pending", "confirmed", "confirmed", "invoiced", "invoiced"]),
            created_by=sales_user.id)
        subtotal = 0
        for _ in range(random.randint(1, 4)):
            it = random.choice(items_list)
            qty = rng(1, 20); up = it.unit_price * rng(1.0, 1.25); total = qty * up
            subtotal += total
            so.items.append(SaleItem(item_id=it.id, item_name=it.name, quantity=qty,
                                      unit_price=round(up, 2), total=round(total, 2)))
        so.subtotal = round(subtotal, 2)
        so.discount_amt = round(subtotal * so.discount_pct / 100, 2)
        so.tax_amt = round((subtotal - so.discount_amt) * so.tax_pct / 100, 2)
        so.total = round(subtotal - so.discount_amt + so.tax_amt, 2)
        db.session.add(so)
    db.session.commit()

    # ── 12. INVENTORY COUNTS ──
    from app.models import InventoryCount, InventoryCountLine
    for _ in range(3):
        wh = random.choice(list(whs.values()))
        ic = InventoryCount(ref_number=ref("CNT"), warehouse_id=wh.id, supervisor_id=keeper.id,
            status=random.choice(["active", "completed"]), started_at=days_ago(random.randint(20, 60)))
        for it in random.sample(items_list, min(8, len(items_list))):
            s = Stock.query.filter_by(item_id=it.id, warehouse_id=wh.id).first()
            sq = s.quantity if s else 0
            ic.lines.append(InventoryCountLine(item_id=it.id, system_quantity=sq,
                actual_quantity=sq * rng(0.95, 1.05) if ic.status == "completed" else None))
        if ic.status == "completed": ic.completed_at = days_ago(5)
        db.session.add(ic)
    db.session.commit()

    # ── 13. NOTIFICATIONS ──
    for u in usr_map.values():
        for _ in range(3):
            n = Notification(type=random.choice(["info", "success", "warning"]),
                title=random.choice(["تم وصول شحنة جديدة", "صنف وصل للحد الحرج", "تأكيد أمر بيع",
                    "إستلام بضاعة", "تحويل معلق", "تم إضافة صنف جديد"]),
                message="بيانات تجريبية", user_id=u.id, is_read=random.random() > 0.6,
                created_at=days_ago(random.randint(1, 30)))
            db.session.add(n)
    db.session.commit()

    # ── 14. LOTS ──
    for it in items_list[:5]:
        for _ in range(random.randint(1, 2)):
            db.session.add(Lot(item_id=it.id, lot_number=f"LOT-{random.randint(1000,9999)}",
                expiry_date=date_ago(-random.randint(30, 365)),
                status=random.choice(["active", "active", "expired"])))
    db.session.commit()

    # ── 15. SCHEDULED COUNTS ──
    for wh_id in [w.id for w in whs.values()]:
        db.session.add(ScheduledCount(warehouse_id=wh_id, frequency="monthly", day_of_month=1, is_active=True))
    db.session.commit()

    # ── 16. PURCHASE RETURNS ──
    for i in range(3):
        pr = PurchaseReturn(ref_number=ref("RET"), supplier_id=random.choice(supps).id,
            warehouse_id=random.choice(list(whs.values())).id,
            reason=random.choice(["damaged", "wrong_item", "over_supply"]),
            status=random.choice(["approved", "returned", "pending"]))
        for _ in range(random.randint(1, 3)):
            it = random.choice(items_list); qty = rng(1, 10)
            pr.items.append(PReturnItem(item_id=it.id, item_name=it.name, quantity=qty,
                unit_price=it.unit_price, total=qty * it.unit_price))
        db.session.add(pr)
    db.session.commit()

    # ── 17. PROJECT INVOICES ──
    for p in projs:
        for _ in range(random.randint(2, 4)):
            db.session.add(ProjectInvoice(project_id=p.id, ref_number=ref("INV"),
                amount=rng(100000, 5000000), description=f"دفعة لمشروع {p.name}",
                status=random.choice(["pending", "approved", "paid", "paid"]),
                invoice_date=date_ago(random.randint(10, 180))))
    db.session.commit()

    return {
        "ok": True,
        "msg": "تم إنشاء البيانات التجريبية بنجاح",
        "stats": {
            "warehouses": Warehouse.query.count(),
            "categories": Category.query.count(),
            "items": Item.query.count(),
            "suppliers": Supplier.query.count(),
            "users": User.query.count(),
            "projects": Project.query.count(),
            "movements": StockMovement.query.count(),
            "transfers": Transfer.query.count(),
            "purchase_orders": PurchaseOrder.query.count(),
            "sales": SaleOrder.query.count(),
        }
    }

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        res = seed_all(force=True)
        print(res["msg"])
        for k, v in res["stats"].items():
            print(f"  {k}: {v}")
