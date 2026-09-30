from django.db.models import Sum
from .models import Sale

def navigation(request):
    return {
        "nav_items": [("dashboard", "Dashboard"), ("sales", "Sales"), ("inventory", "Inventory"), ("products", "Products"), ("suppliers", "Suppliers"), ("reports", "Reports"), ("settings", "Settings")],
        "cumulative_sales": Sale.objects.exclude(status=Sale.Status.VOID).aggregate(value=Sum("total_amount"))["value"] or 0,
        "active_nav": getattr(getattr(request, "resolver_match", None), "url_name", ""),
    }
