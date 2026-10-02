import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from datetime import datetime, time
from functools import wraps
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import Sum, Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from .forms import ProductForm, SupplierForm, UserForm
from .models import AuditLog, Product, ReturnRecord, Sale, SaleItem, StockMovement, Supplier, User

def admin_only(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated: return redirect_to_login(request.get_full_path())
        if not request.user.can_manage: return HttpResponseForbidden("Administrator access required.")
        return view(request, *args, **kwargs)
    return wrapped

def log_action(user, action, entity, entity_id="", previous=None, new=None):
    AuditLog.objects.create(actor=user, actor_name=user.get_full_name() or user.username, action=action,
                            entity_type=entity, entity_id=str(entity_id), previous_value=previous, new_value=new)

def date_range(key):
    now = timezone.localtime()
    today = now.date()
    if key == "yesterday": start, end = today - timedelta(days=1), today
    elif key == "week": start, end = today - timedelta(days=today.weekday()), today + timedelta(days=1)
    elif key == "month": start, end = today.replace(day=1), today + timedelta(days=1)
    elif key == "all": return None, None
    else: start, end = today, today + timedelta(days=1)
    return start, end

def sales_in_range(key):
    sales = Sale.objects.exclude(status=Sale.Status.VOID)
    start, end = date_range(key)
    if start is not None: sales = sales.filter(created_at__date__gte=start, created_at__date__lt=end)
    return sales

@login_required
def dashboard(request):
    if not request.user.can_manage: return redirect("sales")
    today_sales = sales_in_range("today")
    month_sales = sales_in_range("month")
    all_sales = sales_in_range("all")
    stock = Product.objects.filter(track_stock=True)
    metrics = {
        "today_sales": today_sales.aggregate(v=Sum("total_amount"))["v"] or 0,
        "today_transactions": today_sales.count(),
        "stock_units": stock.aggregate(v=Sum("current_stock"))["v"] or 0,
        "product_count": Product.objects.count(),
        "low_stock": stock.filter(current_stock__gt=0, current_stock__lte=models_f("minimum_stock")).count(),
        "out_stock": stock.filter(current_stock=0).count(),
        "stock_value": sum((p.cost_price * p.current_stock for p in stock), Decimal("0")),
        "all_sales": all_sales.aggregate(v=Sum("total_amount"))["v"] or 0,
        "month_sales": month_sales.aggregate(v=Sum("total_amount"))["v"] or 0,
        "today_profit": today_sales.filter(sale_type=Sale.Type.PRODUCT).aggregate(v=Sum("gross_profit"))["v"] or 0,
        "month_profit": month_sales.filter(sale_type=Sale.Type.PRODUCT).aggregate(v=Sum("gross_profit"))["v"] or 0,
        "total_items_sold": SaleItem.objects.filter(item_type="stock").aggregate(v=Sum("quantity"))["v"] or 0,
    }
    alerts = stock.filter(current_stock__lte=models_f("minimum_stock")).order_by("current_stock")
    days = []
    for offset in range(6, -1, -1):
        day = timezone.localdate() - timedelta(days=offset)
        amount = Sale.objects.filter(created_at__date=day).exclude(status=Sale.Status.VOID).aggregate(v=Sum("total_amount"))["v"] or 0
        days.append({"label": day.strftime("%m-%d"), "amount": amount})
    max_day = max([d["amount"] for d in days] + [1])
    for day in days: day["width"] = max(4, int(day["amount"] / max_day * 100))
    best = SaleItem.objects.values("product_name").annotate(qty=Sum("quantity")).order_by("-qty")[:5]
    max_best = max([x["qty"] for x in best] + [1])
    best = [{**x, "width": int(x["qty"] / max_best * 100)} for x in best]
    return render(request, "manager/dashboard.html", {"metrics": metrics, "alerts": alerts, "days": days, "best": best})

def models_f(field):
    from django.db.models import F
    return F(field)

@login_required
def sales(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                products = request.POST.getlist("product_id[]")
                quantities = request.POST.getlist("quantity[]")
                custom_names = request.POST.getlist("custom_name[]")
                custom_prices = request.POST.getlist("custom_price[]")
                lines = []
                for i, selected in enumerate(products):
                    qty = int(quantities[i] or 1)
                    if qty < 1: raise ValueError("Quantity must be at least one.")
                    if selected == "custom":
                        name = (custom_names[i] or "Custom Company Stamp").strip()
                        price = Decimal(custom_prices[i] or "0")
                        if price < 0: raise ValueError("Price cannot be negative.")
                        lines.append((None, name, qty, price, Decimal("0"), "custom"))
                    elif selected:
                        p = Product.objects.select_for_update().get(pk=int(selected), active=True, track_stock=True)
                        lines.append((p, p.name, qty, p.selling_price, p.cost_price, "stock"))
                if not lines: raise ValueError("Add at least one sale item.")
                for p, name, qty, price, cost, kind in lines:
                    if p and p.current_stock < qty: raise ValueError(f"Insufficient stock. Only {p.current_stock} units are available for {p.name}.")
                total = sum((qty * price for p, name, qty, price, cost, kind in lines), Decimal("0"))
                profit = sum((qty * (price - cost) for p, name, qty, price, cost, kind in lines), Decimal("0"))
                next_number = (Sale.objects.count() + 1)
                sale = Sale.objects.create(sale_number=f"SALE-{next_number:05d}", customer_name=request.POST.get("customer_name", "").strip(), payment_method=request.POST.get("payment_method", "Cash"), notes=request.POST.get("notes", "").strip(), total_amount=total, gross_profit=profit, created_by=request.user)
                sale_day = parse_date(request.POST.get("date", ""))
                if sale_day:
                    sale.created_at = timezone.make_aware(datetime.combine(sale_day, timezone.localtime().time().replace(tzinfo=None)))
                    sale.save(update_fields=["created_at"])
                for p, name, qty, price, cost, kind in lines:
                    SaleItem.objects.create(sale=sale, product=p, product_name=name, item_type=kind, quantity=qty, unit_price=price, cost_price=cost)
                    if p:
                        before = p.current_stock; p.current_stock -= qty; p.save(update_fields=["current_stock", "updated_at"])
                        StockMovement.objects.create(product=p, product_name=p.name, movement_type="SALE", quantity=-qty, previous_stock=before, new_stock=p.current_stock, reference=sale.sale_number, notes="Sale recorded", related_sale=sale, created_by=request.user)
                log_action(request.user, "CREATE_SALE", "Sale", sale.pk, new={"sale_number": sale.sale_number, "total": str(total)})
            messages.success(request, f"{sale.sale_number} saved. Stock and sales totals updated.")
        except (ValueError, InvalidOperation, Product.DoesNotExist, IndexError) as exc:
            messages.error(request, str(exc) or "Check sale details and try again.")
        return redirect("sales")
    query = request.GET.get("q", "")
    payment = request.GET.get("payment", "")
    listing = Sale.objects.prefetch_related("items").order_by("-created_at")
    if not request.user.can_manage: listing = listing.filter(created_by=request.user)
    if query: listing = listing.filter(sale_number__icontains=query) | listing.filter(customer_name__icontains=query)
    if payment: listing = listing.filter(payment_method=payment)
    return render(request, "manager/sales.html", {"products": Product.objects.filter(active=True, track_stock=True), "sales": listing, "query": query, "payment": payment, "payments": Sale.Payment.choices})

@login_required
def wood_stamp_sales(request):
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", "0"))
            price = Decimal(request.POST.get("unit_price", ""))
            description = request.POST.get("description", "").strip()
            if quantity < 1: raise ValueError("Quantity must be at least one.")
            if price < 0: raise ValueError("Selling price cannot be negative.")
            if not description: raise ValueError("Enter a Wood Stamp description/type.")
            with transaction.atomic():
                sale_number = f"SALE-{Sale.objects.count() + 1:05d}"
                sale = Sale.objects.create(
                    sale_number=sale_number, sale_type=Sale.Type.WOOD_STAMP,
                    customer_name=request.POST.get("customer_name", "").strip(),
                    payment_method=request.POST.get("payment_method", "Cash"),
                    total_amount=quantity * price, gross_profit=Decimal("0"),
                    created_by=request.user,
                )
                sale_day = parse_date(request.POST.get("date", ""))
                if sale_day:
                    sale.created_at = timezone.make_aware(datetime.combine(sale_day, timezone.localtime().time().replace(tzinfo=None)))
                    sale.save(update_fields=["created_at"])
                SaleItem.objects.create(sale=sale, product=None, product_name=description,
                                        item_type="wood_stamp", quantity=quantity,
                                        unit_price=price, cost_price=None)
                log_action(request.user, "CREATE_WOOD_STAMP_SALE", "Sale", sale.pk,
                           new={"sale_number": sale.sale_number, "total": str(sale.total_amount)})
            messages.success(request, f"{sale.sale_number} saved. Wood Stamp sales do not affect stock or profit.")
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc) or "Check Wood Stamp sale details and try again.")
        return redirect("wood_stamp_sales")
    listing = Sale.objects.filter(sale_type=Sale.Type.WOOD_STAMP).prefetch_related("items").order_by("-created_at")
    if not request.user.can_manage: listing = listing.filter(created_by=request.user)
    return render(request, "manager/wood_stamp_sales.html", {"sales": listing, "payments": Sale.Payment.choices})

@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related("items"), pk=pk)
    if not request.user.can_manage and sale.created_by_id != request.user.pk: return HttpResponseForbidden("You may only view your own sales.")
    return render(request, "manager/sale_detail.html", {"sale": sale, "auto_print": request.GET.get("print") == "1"})

@admin_only
def sale_edit(request, pk):
    with transaction.atomic():
        sale = get_object_or_404(Sale.objects.select_for_update().prefetch_related("items"), pk=pk)
        items = list(sale.items.all())
        if request.method == "POST":
            if sale.status != Sale.Status.COMPLETE:
                messages.error(request, "Only completed sales can be edited. Returns and voids must remain unchanged.")
                return redirect("sale_detail", pk=sale.pk)
            try:
                quantities = request.POST.getlist("quantity[]")
                prices = request.POST.getlist("unit_price[]")
                if len(quantities) != len(items) or len(prices) != len(items):
                    raise ValueError("Sale items changed. Reload the page and try again.")
                changes = []
                for item, qty_text, price_text in zip(items, quantities, prices):
                    qty = int(qty_text); price = Decimal(price_text)
                    if qty < 1 or price < 0: raise ValueError("Quantities must be positive and prices cannot be negative.")
                    changes.append((item, qty, price))
                old_values = {"customer": sale.customer_name, "payment": sale.payment_method,
                              "notes": sale.notes, "total": str(sale.total_amount)}
                customer_name = request.POST.get("customer_name", "").strip()
                payment_method = request.POST.get("payment_method", sale.payment_method)
                if payment_method not in dict(Sale.Payment.choices): raise ValueError("Choose a valid payment method.")
                notes = request.POST.get("notes", "").strip()
                sale_day = parse_date(request.POST.get("date", ""))
                if not sale_day: raise ValueError("Enter a valid sale date.")
                # Reconcile stock by product, accounting for multiple lines of the same product.
                product_deltas = {}
                for item, qty, price in changes:
                    if item.product_id:
                        product_deltas[item.product_id] = product_deltas.get(item.product_id, 0) + qty - item.quantity
                locked_products = {product.pk: product for product in Product.objects.select_for_update().filter(pk__in=product_deltas)}
                for product_id, delta in product_deltas.items():
                    product = locked_products[product_id]
                    if product.current_stock < delta:
                        raise ValueError(f"Insufficient stock to increase {product.name}; only {product.current_stock} units are available.")
                for product_id, delta in product_deltas.items():
                    product = locked_products[product_id]
                    if delta:
                        before = product.current_stock
                        product.current_stock -= delta
                        product.save(update_fields=["current_stock", "updated_at"])
                        StockMovement.objects.create(product=product, product_name=product.name,
                            movement_type="SALE EDIT", quantity=-delta, previous_stock=before,
                            new_stock=product.current_stock, reference=sale.sale_number,
                            notes="Stock reconciled after sale edit", related_sale=sale, created_by=request.user)
                total = Decimal("0"); profit = Decimal("0")
                for item, qty, price in changes:
                    item.quantity = qty; item.unit_price = price; item.save(update_fields=["quantity", "unit_price"])
                    total += qty * price
                    if sale.sale_type != Sale.Type.WOOD_STAMP:
                        profit += qty * (price - (item.cost_price or Decimal("0")))
                sale.customer_name = customer_name
                sale.payment_method = payment_method
                sale.notes = notes
                sale.total_amount = total; sale.gross_profit = profit
                sale.created_at = timezone.make_aware(datetime.combine(sale_day, timezone.localtime(sale.created_at).time().replace(tzinfo=None)))
                sale.save(update_fields=["customer_name", "payment_method", "notes", "total_amount", "gross_profit", "created_at"])
                log_action(request.user, "EDIT_SALE", "Sale", sale.pk, previous=old_values,
                           new={"customer": sale.customer_name, "payment": sale.payment_method,
                                "notes": sale.notes, "total": str(total)})
                messages.success(request, f"{sale.sale_number} updated. Stock and totals were reconciled.")
                return redirect("sale_detail", pk=sale.pk)
            except (ValueError, InvalidOperation) as exc:
                messages.error(request, str(exc) or "Check the sale details and try again.")
    return render(request, "manager/sale_edit.html", {"sale": sale, "items": items, "payments": Sale.Payment.choices,
        "sale_date": timezone.localtime(sale.created_at).date().isoformat()})

@admin_only
def inventory(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if not request.user.can_manage: return HttpResponseForbidden("Administrator access required.")
        try:
            with transaction.atomic():
                p = get_object_or_404(Product.objects.select_for_update(), pk=request.POST.get("product_id"))
                if not p.track_stock: raise ValueError("This product does not track stock.")
                if action == "add_stock":
                    qty = int(request.POST.get("quantity", 0)); cost = Decimal(request.POST.get("cost_price", "0"))
                    if qty <= 0 or cost < 0: raise ValueError("Enter a positive quantity and valid cost.")
                    before = p.current_stock; p.current_stock += qty; p.cost_price = cost
                    p.supplier_name = request.POST.get("supplier", p.supplier_name).strip()
                    p.supplier = Supplier.objects.filter(name__iexact=p.supplier_name).first() if p.supplier_name else None
                    p.save()
                    movement = "STOCK PURCHASE"; ref = "Purchase " + request.POST.get("date", "")
                    note = request.POST.get("notes", "Stock received")
                elif action == "adjust":
                    actual = int(request.POST.get("actual_quantity", -1)); note = request.POST.get("reason", "").strip()
                    if actual < 0 or not note: raise ValueError("Provide an actual quantity and adjustment reason.")
                    before = p.current_stock; p.current_stock = actual; p.save()
                    qty = actual - before; movement = "STOCK ADJUSTMENT"; ref = "Stock count"
                elif action == "return":
                    sale = get_object_or_404(Sale.objects.select_for_update(), pk=request.POST.get("sale_id"))
                    qty = int(request.POST.get("quantity", 0)); note = request.POST.get("reason", "").strip()
                    sold = SaleItem.objects.filter(sale=sale, product=p).aggregate(v=Sum("quantity"))["v"] or 0
                    returned = ReturnRecord.objects.filter(sale=sale, product=p).aggregate(v=Sum("quantity"))["v"] or 0
                    if qty <= 0 or qty > sold - returned or not note: raise ValueError(f"Return exceeds quantity available ({sold-returned}) or has no reason.")
                    item = SaleItem.objects.filter(sale=sale, product=p).first()
                    amount = qty * item.unit_price; before = p.current_stock; p.current_stock += qty; p.save()
                    ReturnRecord.objects.create(sale=sale, product=p, quantity=qty, amount=amount, reason=note, created_by=request.user)
                    sale.total_amount = max(Decimal("0"), sale.total_amount - amount)
                    sale.gross_profit -= qty * (item.unit_price - item.cost_price)
                    sale.status = Sale.Status.RETURNED if sale.total_amount == 0 else Sale.Status.PARTIAL
                    sale.save(update_fields=["total_amount", "gross_profit", "status"])
                    movement = "RETURN"; ref = sale.sale_number
                else: raise ValueError("Unknown inventory action.")
                StockMovement.objects.create(product=p, product_name=p.name, movement_type=movement, quantity=qty, previous_stock=before, new_stock=p.current_stock, reference=ref, notes=note, related_sale=sale if action == "return" else None, created_by=request.user)
                log_action(request.user, action.upper(), "Product", p.pk, previous={"stock": before}, new={"stock": p.current_stock, "quantity": qty})
            messages.success(request, "Inventory updated successfully.")
        except (ValueError, InvalidOperation) as exc: messages.error(request, str(exc))
        return redirect("inventory")
    products = Product.objects.filter(track_stock=True).select_related("supplier").order_by("name")
    q = request.GET.get("q", "")
    if q: products = products.filter(name__icontains=q) | products.filter(category__icontains=q) | products.filter(type__icontains=q) | products.filter(color__icontains=q)
    return render(request, "manager/inventory.html", {"products": products, "all_products": Product.objects.filter(active=True, track_stock=True), "movements": StockMovement.objects.select_related("created_by")[:20], "sales": Sale.objects.exclude(status=Sale.Status.VOID).order_by("-created_at"), "query": q})

@admin_only
def products(request):
    if request.method == "POST":
        if not request.user.can_manage: return HttpResponseForbidden("Administrator access required.")
        form = ProductForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False); p.supplier_name = form.cleaned_data["supplier_text"]
            p.supplier = Supplier.objects.filter(name__iexact=p.supplier_name).first() if p.supplier_name else None
            p.save()
            if p.track_stock and p.current_stock > 0:
                StockMovement.objects.create(product=p, product_name=p.name, movement_type="STOCK PURCHASE", quantity=p.current_stock, previous_stock=0, new_stock=p.current_stock, reference="Opening stock", notes="Initial stock at product creation", created_by=request.user)
            log_action(request.user, "CREATE_PRODUCT", "Product", p.pk, new={"name": p.name})
            messages.success(request, f"{p.name} saved."); return redirect("products")
        messages.error(request, "Please correct the product form.")
    else: form = ProductForm()
    q = request.GET.get("q", "")
    listing = Product.objects.all().order_by("name")
    if q: listing = listing.filter(name__icontains=q) | listing.filter(category__icontains=q) | listing.filter(type__icontains=q) | listing.filter(color__icontains=q)
    return render(request, "manager/products.html", {"products": listing, "form": form, "query": q})

@admin_only
def product_edit(request, pk):
    p = get_object_or_404(Product, pk=pk); before = p.current_stock
    form = ProductForm(request.POST or None, instance=p)
    if request.method == "POST" and form.is_valid():
        p = form.save(commit=False); p.supplier_name = form.cleaned_data["supplier_text"]
        p.supplier = Supplier.objects.filter(name__iexact=p.supplier_name).first() if p.supplier_name else None
        p.save()
        if before != p.current_stock:
            StockMovement.objects.create(product=p, product_name=p.name, movement_type="STOCK ADJUSTMENT", quantity=p.current_stock-before, previous_stock=before, new_stock=p.current_stock, reference="Product edit", notes="Quantity changed in product form", created_by=request.user)
        log_action(request.user, "UPDATE_PRODUCT", "Product", p.pk, previous={"stock": before}, new={"name": p.name, "stock": p.current_stock})
        messages.success(request, f"{p.name} saved."); return redirect("products")
    return render(request, "manager/product_edit.html", {"form": form, "product": p})

@admin_only
def product_toggle(request, pk):
    if request.method == "POST":
        p = get_object_or_404(Product, pk=pk); p.active = not p.active; p.save(update_fields=["active", "updated_at"])
        log_action(request.user, "SET_PRODUCT_STATUS", "Product", p.pk, new={"active": p.active})
        messages.success(request, f"{p.name} is now {'active' if p.active else 'inactive'}.")
    return redirect("products")

@admin_only
def product_history(request, pk):
    p = get_object_or_404(Product, pk=pk)
    return render(request, "manager/product_history.html", {"product": p, "movements": p.movements.select_related("created_by")})

@admin_only
def suppliers(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST":
        if not request.user.can_manage: return HttpResponseForbidden("Administrator access required.")
        if form.is_valid():
            item = form.save(); log_action(request.user, "CREATE_SUPPLIER", "Supplier", item.pk, new={"name": item.name})
            messages.success(request, f"{item.name} saved."); return redirect("suppliers")
        messages.error(request, "Please check the supplier details.")
    return render(request, "manager/suppliers.html", {"form": form, "suppliers": Supplier.objects.all().order_by("name")})

@admin_only
def reports(request):
    period = request.GET.get("period", "today")
    if period not in {"today", "yesterday", "week", "month", "all"}: period = "today"
    listing = sales_in_range(period).prefetch_related("items").order_by("-created_at")
    payments = []
    for label, _ in Sale.Payment.choices:
        amount = listing.filter(payment_method=label).aggregate(v=Sum("total_amount"))["v"] or 0
        payments.append({"label": label, "amount": amount})
    max_amount = max([x["amount"] for x in payments] + [1])
    for x in payments: x["width"] = max(4, int(x["amount"] / max_amount * 100))
    total = listing.aggregate(revenue=Sum("total_amount"), profit=Sum("gross_profit"))["revenue"] or 0
    profit = listing.filter(sale_type=Sale.Type.PRODUCT).aggregate(v=Sum("gross_profit"))["v"] or 0
    item_count = SaleItem.objects.filter(sale__in=listing).aggregate(v=Sum("quantity"))["v"] or 0
    stock = list(Product.objects.filter(track_stock=True).order_by("current_stock")[:8])
    max_stock = max([p.current_stock for p in stock] + [1])
    for p in stock: p.chart_width = max(4, int(p.current_stock / max_stock * 100))
    return render(request, "manager/reports.html", {"sales": listing, "period": period, "period_options": [("today", "Today"), ("yesterday", "Yesterday"), ("week", "This week"), ("month", "This month"), ("all", "Cumulative")], "payments": payments, "revenue": total, "profit": profit, "item_count": item_count, "stock": stock})

@admin_only
def settings_page(request):
    form = UserForm()
    return render(request, "manager/settings.html", {"users": User.objects.filter(is_active=True), "audit": AuditLog.objects.all()[:30], "form": form})

@admin_only
def add_user(request):
    form = UserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(); log_action(request.user, "CREATE_USER", "User", user.pk, new={"username": user.username, "role": user.role})
        messages.success(request, f"{user.username} added."); return redirect("settings")
    messages.error(request, "Please check the new user details and password.")
    return redirect("settings")

@admin_only
def switch_user(request, pk):
    if request.method == "POST":
        user = get_object_or_404(User, pk=pk, is_active=True); login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Signed in as {user.get_full_name() or user.username} ({user.role}).")
    return redirect(request.POST.get("next", "dashboard"))

@admin_only
def backup(request):
    data = {
        "products": list(Product.objects.values()), "suppliers": list(Supplier.objects.values()),
        "sales": list(Sale.objects.values()), "sale_items": list(SaleItem.objects.values()),
        "stock_movements": list(StockMovement.objects.values()), "returns": list(ReturnRecord.objects.values()),
        "audit_logs": list(AuditLog.objects.values()),
    }
    response = HttpResponse(json.dumps(data, default=str, indent=2), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="stamp-manager-backup-{timezone.localdate()}.json"'
    return response

@admin_only
def reset_sample(request):
    if request.method == "POST":
        with transaction.atomic():
            ReturnRecord.objects.all().delete(); StockMovement.objects.all().delete(); SaleItem.objects.all().delete(); Sale.objects.all().delete(); AuditLog.objects.all().delete(); Product.objects.all().delete(); Supplier.objects.all().delete()
            from .management.commands.seed_sample import seed
            seed(actor=request.user)
        messages.success(request, "Sample data reset.")
    return redirect("settings")
