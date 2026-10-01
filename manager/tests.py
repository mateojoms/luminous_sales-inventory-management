from django.test import TestCase
from django.urls import reverse
from manager.models import Product, Sale, SaleItem, User

class SalesAccessTests(TestCase):
    def setUp(self):
        self.sales_user = User.objects.create_user(username="seller", password="StrongPass123!", role=User.Role.SALES)
        self.admin = User.objects.create_user(username="admin", password="StrongPass123!", role=User.Role.ADMIN)

    def test_sales_user_login_and_restricted_urls(self):
        self.assertTrue(self.client.login(username="seller", password="StrongPass123!"))
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("sales"))
        for url in ("reports", "settings", "inventory", "products", "suppliers", "backup"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(reverse(url)).status_code, 403)
        response = self.client.get(reverse("sales"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wood Stamp")
        response = self.client.get(reverse("wood_stamp_sales"))
        self.assertEqual(response.status_code, 200)
        for forbidden in ("Dashboard", "Reports", "Settings"):
            self.assertNotContains(response, forbidden)

    def test_admin_keeps_restricted_access(self):
        self.client.login(username="admin", password="StrongPass123!")
        for url in ("dashboard", "reports", "settings", "inventory", "products", "suppliers", "backup"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(reverse(url)).status_code, 200)

    def test_sales_user_can_only_view_own_sale_detail(self):
        sale = Sale.objects.create(sale_number="SALE-00001", created_by=self.admin)
        self.client.login(username="seller", password="StrongPass123!")
        self.assertEqual(self.client.get(reverse("sale_detail", args=[sale.pk])).status_code, 403)

class WoodStampSalesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seller", password="StrongPass123!", role=User.Role.SALES)
        self.client.login(username="seller", password="StrongPass123!")
        self.product = Product.objects.create(name="Rubber Stamp", selling_price=1000, cost_price=600, current_stock=10)

    def test_wood_stamp_revenue_no_cost_profit_or_stock_change(self):
        response = self.client.post(reverse("wood_stamp_sales"), {
            "date": "2026-10-01", "description": "Oak handle stamp", "quantity": "2",
            "unit_price": "500", "customer_name": "Test customer", "payment_method": "Cash",
        })
        self.assertRedirects(response, reverse("wood_stamp_sales"))
        stamp_sale = Sale.objects.get(sale_type=Sale.Type.WOOD_STAMP)
        item = stamp_sale.items.get()
        self.assertEqual(stamp_sale.total_amount, 1000)
        self.assertEqual(stamp_sale.gross_profit, 0)
        self.assertIsNone(item.product_id)
        self.assertIsNone(item.cost_price)
        self.assertEqual(self.product.current_stock, 10)
        self.assertContains(self.client.get(reverse("wood_stamp_sales")), "Wood Stamp")
        self.assertContains(self.client.get(reverse("sales")), "Wood Stamp")
        self.assertNotContains(self.client.get(reverse("sale_detail", args=[stamp_sale.pk])), "Gross profit")

    def test_normal_sale_profit_stock_and_combined_totals(self):
        self.client.post(reverse("sales"), {
            "product_id[]": str(self.product.pk), "quantity[]": "2", "date": "2026-10-01",
            "customer_name": "", "payment_method": "Cash", "notes": "",
            "custom_name[]": "", "custom_price[]": "0",
        })
        self.client.post(reverse("wood_stamp_sales"), {
            "date": "2026-10-01", "description": "Oak stamp", "quantity": "2", "unit_price": "500",
            "payment_method": "Cash",
        })
        self.product.refresh_from_db()
        product_sale = Sale.objects.get(sale_type=Sale.Type.PRODUCT)
        self.assertEqual(product_sale.total_amount, 2000)
        self.assertEqual(product_sale.gross_profit, 800)
        self.assertEqual(self.product.current_stock, 8)
        self.assertEqual(sum(Sale.objects.values_list("total_amount", flat=True)), 3000)
        self.assertEqual(sum(Sale.objects.values_list("gross_profit", flat=True)), 800)
        self.assertEqual(Sale.objects.filter(created_at__date="2026-10-01").count(), 2)
        admin = User.objects.create_user(username="admin", password="StrongPass123!", role=User.Role.ADMIN)
        self.client.force_login(admin)
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, "KES 3,000")
        self.assertContains(dashboard, "KES 800")
        report = self.client.get(reverse("reports"), {"period": "all"})
        self.assertContains(report, "KES 3,000")
        self.assertContains(report, "KES 800")
