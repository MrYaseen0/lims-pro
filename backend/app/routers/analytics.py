"""Analytics dashboard route."""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.deps import get_current_user
from app.models.schemas import OrderStatus


router = APIRouter()


@router.get("/analytics/dashboard", response_model=dict)
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's stats
    today_orders = await db.orders.count_documents({"created_at": {"$gte": today.isoformat()}})
    today_patients = await db.patients.count_documents({"created_at": {"$gte": today.isoformat()}})
    
    # Revenue stats
    invoices_today = await db.invoices.find({"created_at": {"$gte": today.isoformat()}}, {"_id": 0, "net_amount": 1}).to_list(1000)
    today_revenue = sum(inv.get("net_amount", 0) for inv in invoices_today)
    
    invoices_month = await db.invoices.find({"created_at": {"$gte": month_ago.isoformat()}}, {"_id": 0, "net_amount": 1}).to_list(10000)
    month_revenue = sum(inv.get("net_amount", 0) for inv in invoices_month)
    
    # Pending work
    pending_samples = await db.orders.count_documents({"status": OrderStatus.REGISTERED})
    pending_results = await db.orders.count_documents({"status": {"$in": [OrderStatus.SAMPLE_COLLECTED, OrderStatus.IN_LAB]}})
    pending_approval = await db.orders.count_documents({"status": OrderStatus.UNDER_REVIEW})
    
    # Test volume by category
    test_volumes = []
    categories = await db.tests.distinct("category")
    for cat in categories:
        tests_in_cat = await db.tests.find({"category": cat}, {"_id": 0, "id": 1}).to_list(100)
        test_ids = [t["id"] for t in tests_in_cat]
        count = 0
        orders = await db.orders.find({}, {"_id": 0, "tests": 1}).to_list(10000)
        for order in orders:
            for test in order.get("tests", []):
                if test.get("test_id") in test_ids:
                    count += 1
        test_volumes.append({"category": cat, "count": count})
    
    # Daily revenue for chart (last 7 days)
    daily_revenue = []
    for i in range(7):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        day_invoices = await db.invoices.find({
            "created_at": {"$gte": day.isoformat(), "$lt": next_day.isoformat()}
        }, {"_id": 0, "net_amount": 1}).to_list(1000)
        daily_revenue.append({
            "date": day.strftime("%Y-%m-%d"),
            "revenue": sum(inv.get("net_amount", 0) for inv in day_invoices)
        })
    
    return {
        "today_orders": today_orders,
        "today_patients": today_patients,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "pending_samples": pending_samples,
        "pending_results": pending_results,
        "pending_approval": pending_approval,
        "test_volumes": test_volumes,
        "daily_revenue": list(reversed(daily_revenue)),
        "total_patients": await db.patients.count_documents({}),
        "total_tests": await db.tests.count_documents({"is_active": True})
    }
