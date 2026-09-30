from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.core.management import CommandError
from manager.models import Product, StockMovement, Supplier, User

@transaction.atomic
def seed(actor=None):
    supplier_data = [
        ("Nairobi Stationers", "+254 700 000 001", "sales@nairobi-stationers.example", "Nairobi CBD", "Stamp bodies and office supplies"),
        ("Ink World", "+254 700 000 002", "orders@inkworld.example", "Industrial Area", "Ink refills"),
        ("Print Supplies Ltd", "+254 700 000 003", "hello@printsupplies.example", "Mombasa Road", "Pads and accessories"),
    ]
    suppliers = {name: Supplier.objects.get_or_create(name=name, defaults={"phone": phone, "email": email, "address": address, "notes": notes})[0]
                 for name, phone, email, address, notes in supplier_data}
    product_data = [
        ("Self-Inking Stamp", "Stamp", "Trodat-style office stamp", 300, 600, 20, 5, "Nairobi Stationers", "Self-Inking", "", ""),
        ("Black Stamp Ink", "Ink", "General-purpose refill ink", 100, 200, 10, 3, "Ink World", "", "Black", "30ml"),
        ("Large Stamp Pad", "Stamp Pad", "Desktop stamp pad", 150, 300, 4, 5, "Print Supplies Ltd", "Large", "Blue", ""),
        ("Custom Logo Stamp Service", "Custom Order", "Made-to-order company stamp", 0, 800, 0, 0, "In-house", "", "", ""),
    ]
    for name, category, desc, cost, price, stock, minimum, supplier_name, kind, color, size in product_data:
        product, created = Product.objects.get_or_create(name=name, defaults={"category": category, "description": desc, "cost_price": cost, "selling_price": price, "current_stock": stock, "minimum_stock": minimum, "supplier": suppliers.get(supplier_name), "supplier_name": supplier_name, "type": kind, "color": color, "size_volume": size, "track_stock": category != "Custom Order"})
        if created and product.track_stock and stock:
            StockMovement.objects.create(product=product, product_name=name, movement_type="STOCK PURCHASE", quantity=stock, previous_stock=0, new_stock=stock, reference="Opening stock", notes="Initial sample stock", created_by=actor)
    if not User.objects.filter(username="owner").exists():
        owner = User.objects.create_superuser(username="owner", password="stamp1234", role=User.Role.ADMIN, first_name="Owner", last_name="Administrator")
        if actor is None: actor = owner
    if not User.objects.filter(username="cashier").exists():
        User.objects.create_user(username="cashier", password="cashier1234", role=User.Role.SALES, first_name="Sales Counter", last_name="User")

class Command(BaseCommand):
    help = "Create starter stamp shop data and demo accounts."
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Sample accounts and data can only be created when DEBUG is enabled.")
        seed()
        self.stdout.write(self.style.SUCCESS("Sample data is ready. Demo accounts: owner / stamp1234 and cashier / cashier1234."))
