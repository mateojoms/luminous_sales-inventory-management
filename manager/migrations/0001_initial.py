import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name="username")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("role", models.CharField(choices=[("Administrator", "Administrator"), ("Sales User", "Sales User")], default="Sales User", max_length=20)),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={"verbose_name": "user", "verbose_name_plural": "users", "abstract": False},
            managers=[("objects", django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(name="Supplier", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=160, unique=True)), ("phone", models.CharField(blank=True, max_length=40)),
            ("email", models.EmailField(blank=True, max_length=254)), ("address", models.CharField(blank=True, max_length=240)),
            ("notes", models.TextField(blank=True)), ("active", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="Product", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=180, unique=True)),
            ("category", models.CharField(choices=[("Stamp", "Stamp"), ("Ink", "Ink"), ("Stamp Pad", "Stamp Pad"), ("Custom Order", "Custom Order"), ("Other", "Other")], default="Other", max_length=30)),
            ("description", models.TextField(blank=True)), ("cost_price", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
            ("selling_price", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("current_stock", models.PositiveIntegerField(default=0)),
            ("minimum_stock", models.PositiveIntegerField(default=0)), ("supplier_name", models.CharField(blank=True, max_length=160)),
            ("active", models.BooleanField(default=True)), ("track_stock", models.BooleanField(default=True)),
            ("type", models.CharField(blank=True, max_length=80)), ("color", models.CharField(blank=True, max_length=80)),
            ("size_volume", models.CharField(blank=True, max_length=80)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("supplier", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="manager.supplier")),
        ]),
        migrations.CreateModel(name="Sale", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("sale_number", models.CharField(max_length=24, unique=True)),
            ("customer_name", models.CharField(blank=True, max_length=180)), ("payment_method", models.CharField(choices=[("Cash", "Cash"), ("M-Pesa", "M-Pesa"), ("Bank", "Bank"), ("Other", "Other")], default="Cash", max_length=20)),
            ("notes", models.TextField(blank=True)), ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ("gross_profit", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ("status", models.CharField(choices=[("COMPLETED", "Completed"), ("PARTIAL RETURN", "Partial return"), ("RETURNED", "Returned"), ("VOID", "Void")], default="COMPLETED", max_length=20)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales", to="manager.user")),
        ]),
        migrations.CreateModel(name="SaleItem", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("product_name", models.CharField(max_length=180)), ("item_type", models.CharField(choices=[("stock", "Stock"), ("custom", "Custom")], default="stock", max_length=12)),
            ("quantity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])), ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
            ("cost_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sale_items", to="manager.product")),
            ("sale", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="manager.sale")),
        ]),
        migrations.CreateModel(name="ReturnRecord", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("quantity", models.PositiveIntegerField()),
            ("amount", models.DecimalField(decimal_places=2, max_digits=12)), ("reason", models.TextField()), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="manager.user")),
            ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="returns", to="manager.product")),
            ("sale", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="returns", to="manager.sale")),
        ]),
        migrations.CreateModel(name="StockMovement", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("product_name", models.CharField(max_length=180)),
            ("movement_type", models.CharField(max_length=32)), ("quantity", models.IntegerField()), ("previous_stock", models.IntegerField()),
            ("new_stock", models.IntegerField()), ("reference", models.CharField(blank=True, max_length=180)), ("notes", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="manager.user")),
            ("product", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movements", to="manager.product")),
            ("related_sale", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movements", to="manager.sale")),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="AuditLog", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("actor_name", models.CharField(blank=True, max_length=150)),
            ("action", models.CharField(max_length=60)), ("entity_type", models.CharField(max_length=50)), ("entity_id", models.CharField(blank=True, max_length=80)),
            ("previous_value", models.JSONField(blank=True, null=True)), ("new_value", models.JSONField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="manager.user")),
        ], options={"ordering": ["-created_at"]}),
    ]
