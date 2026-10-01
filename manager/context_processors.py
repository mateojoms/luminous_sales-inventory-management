from django.db.models import Sum
from .models import Sale

def navigation(request):
    items = [("sales", "Sales"), ("wood_stamp_sales", "Wood Stamps")]
    if getattr(request.user, "can_manage", False):
        items = [("dashboard", "Dashboard"), *items, ("inventory", "Inventory"), ("products", "Products"), ("suppliers", "Suppliers"), ("reports", "Reports"), ("settings", "Settings")]
    sales_total = Sale.objects.exclude(status=Sale.Status.VOID)
    if getattr(request, "user", None) and request.user.is_authenticated and not request.user.can_manage:
        sales_total = sales_total.filter(created_by=request.user)
    return {
        "nav_items": items,
        "cumulative_sales": sales_total.aggregate(value=Sum("total_amount"))["value"] or 0,
        "active_nav": getattr(getattr(request, "resolver_match", None), "url_name", ""),
    }
