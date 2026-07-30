"""استعلامات التقارير المشتركة — shared report queries

The same aggregations feed the JSON endpoints and the CSV/Excel/PDF exports,
so they live here once instead of being re-written per output format.
"""
import datetime
from sqlalchemy import func
from app.models import (db, Item, Stock, StockMovement, Supplier,
                        PurchaseOrder, GoodsReceipt, SupplierEvaluation,
                        InventoryCount, InventoryCountLine, InventoryLayer)

CONSUMPTION_TYPES = ["out", "transfer", "damage"]


def since_days(days):
    return datetime.datetime.utcnow() - datetime.timedelta(days=days)


def consumption_rows(days=30, limit=50, order="desc"):
    """Consumed quantity/value per item over `days`.

    Rows expose item_id, item_name, item_code, item_unit, total_qty,
    total_value and movements.
    """
    total_qty = func.sum(StockMovement.quantity)
    return (db.session.query(
                StockMovement.item_id.label("item_id"),
                Item.name.label("item_name"),
                Item.code.label("item_code"),
                Item.unit.label("item_unit"),
                total_qty.label("total_qty"),
                func.sum(StockMovement.quantity * StockMovement.unit_price).label("total_value"),
                func.count(StockMovement.id).label("movements"))
            .join(Item, StockMovement.item_id == Item.id)
            .filter(StockMovement.type.in_(CONSUMPTION_TYPES),
                    StockMovement.created_at >= since_days(days))
            .group_by(StockMovement.item_id)
            .order_by(total_qty.asc() if order == "asc" else total_qty.desc())
            .limit(limit).all())


def fast_slow_rows(days=90, limit=10):
    """(fast, slow) item rows ranked by consumption over `days`.

    Slow movers are items with no consumption, ranked by idle stock. Rows
    expose item_id, item_name, item_code, item_unit, unit_price, consumed
    and current_stock.
    """
    out_q = (db.session.query(StockMovement.item_id,
                              func.sum(StockMovement.quantity).label("qty"))
             .filter(StockMovement.type.in_(CONSUMPTION_TYPES),
                     StockMovement.created_at >= since_days(days))
             .group_by(StockMovement.item_id).subquery())
    rows = (db.session.query(
                Item.id.label("item_id"),
                Item.name.label("item_name"),
                Item.code.label("item_code"),
                Item.unit.label("item_unit"),
                Item.unit_price.label("unit_price"),
                func.coalesce(out_q.c.qty, 0).label("consumed"),
                func.coalesce(func.sum(Stock.quantity), 0).label("current_stock"))
            .outerjoin(out_q, Item.id == out_q.c.item_id)
            .outerjoin(Stock, Stock.item_id == Item.id)
            .group_by(Item.id).all())
    fast = sorted(rows, key=lambda r: float(r.consumed or 0), reverse=True)[:limit]
    slow = sorted([r for r in rows if float(r.consumed or 0) <= 0],
                  key=lambda r: float(r.current_stock or 0), reverse=True)[:limit]
    return fast, slow


def supplier_performance_rows():
    """PO/GRN totals per supplier — supplier_id, supplier_name, po_count,
    total_amount, grn_count."""
    return (db.session.query(
                Supplier.id.label("supplier_id"),
                Supplier.name.label("supplier_name"),
                func.count(PurchaseOrder.id).label("po_count"),
                func.sum(PurchaseOrder.total_amount).label("total_amount"),
                func.count(GoodsReceipt.id).label("grn_count"))
            .outerjoin(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
            .outerjoin(GoodsReceipt, GoodsReceipt.po_id == PurchaseOrder.id)
            .group_by(Supplier.id).all())


def supplier_evaluation_map():
    """{supplier_id: {"quality","delivery","price"}} averaged over evaluations."""
    rows = (SupplierEvaluation.query.with_entities(
                SupplierEvaluation.supplier_id,
                func.avg(SupplierEvaluation.quality_score).label("avg_quality"),
                func.avg(SupplierEvaluation.delivery_accuracy).label("avg_delivery"),
                func.avg(SupplierEvaluation.price_competitiveness).label("avg_price"))
            .group_by(SupplierEvaluation.supplier_id).all())
    return {r[0]: {"quality": round(float(r[1] or 0), 1),
                   "delivery": round(float(r[2] or 0), 1),
                   "price":    round(float(r[3] or 0), 1)} for r in rows}


def count_difference_lines():
    """Count lines of completed counts whose actual quantity differs."""
    return (db.session.query(InventoryCountLine)
            .join(InventoryCount)
            .filter(InventoryCountLine.actual_quantity.isnot(None),
                    InventoryCountLine.actual_quantity != InventoryCountLine.system_quantity,
                    InventoryCount.status == "completed")
            .order_by(InventoryCount.completed_at.desc())
            .all())


def valuation_rows():
    """(item, valuation) pairs for active items that still hold FIFO layers."""
    rows = []
    for item in Item.query.filter_by(is_active=True).order_by(Item.name).all():
        v = InventoryLayer.get_valuation(item.id)
        if v["total_qty"] > 0:
            rows.append((item, v))
    return rows
