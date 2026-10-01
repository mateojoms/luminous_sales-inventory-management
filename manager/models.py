from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "Administrator", "Administrator"
        SALES = "Sales User", "Sales User"
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SALES)
    @property
    def can_manage(self):
        return self.is_superuser or self.role == self.Role.ADMIN

class Supplier(models.Model):
    name = models.CharField(max_length=160, unique=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=240, blank=True)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class Product(models.Model):
    class Category(models.TextChoices):
        STAMP = "Stamp", "Stamp"
        INK = "Ink", "Ink"
        PAD = "Stamp Pad", "Stamp Pad"
        CUSTOM = "Custom Order", "Custom Order"
        OTHER = "Other", "Other"
    name = models.CharField(max_length=180, unique=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=0)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    supplier_name = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)
    track_stock = models.BooleanField(default=True)
    type = models.CharField(max_length=80, blank=True)
    color = models.CharField(max_length=80, blank=True)
    size_volume = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    @property
    def stock_status(self):
        if not self.track_stock: return "Custom Order"
        if self.current_stock <= 0: return "Out of Stock"
        if self.current_stock <= self.minimum_stock: return "Low Stock"
        return "In Stock"
    def __str__(self): return self.name

class Sale(models.Model):
    class Type(models.TextChoices):
        PRODUCT = "product", "Normal Product Sale"
        WOOD_STAMP = "wood_stamp", "Wood Stamp"
    class Payment(models.TextChoices):
        CASH = "Cash", "Cash"
        MPESA = "M-Pesa", "M-Pesa"
        BANK = "Bank", "Bank"
        OTHER = "Other", "Other"
    class Status(models.TextChoices):
        COMPLETE = "COMPLETED", "Completed"
        PARTIAL = "PARTIAL RETURN", "Partial return"
        RETURNED = "RETURNED", "Returned"
        VOID = "VOID", "Void"
    sale_number = models.CharField(max_length=24, unique=True)
    sale_type = models.CharField(max_length=20, choices=Type.choices, default=Type.PRODUCT)
    customer_name = models.CharField(max_length=180, blank=True)
    payment_method = models.CharField(max_length=20, choices=Payment.choices, default=Payment.CASH)
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETE)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="sales")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.sale_number

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="sale_items")
    product_name = models.CharField(max_length=180)
    item_type = models.CharField(max_length=20, choices=[("stock", "Stock"), ("custom", "Custom"), ("wood_stamp", "Wood Stamp")], default="stock")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    @property
    def subtotal(self): return self.quantity * self.unit_price
    @property
    def item_profit(self):
        if self.item_type == "wood_stamp": return None
        return self.quantity * (self.unit_price - (self.cost_price or Decimal("0")))

class StockMovement(models.Model):
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL, related_name="movements")
    product_name = models.CharField(max_length=180)
    movement_type = models.CharField(max_length=32)
    quantity = models.IntegerField()
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    reference = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    related_sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]

class ReturnRecord(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="returns")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="returns")
    quantity = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    actor_name = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=60)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=80, blank=True)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
