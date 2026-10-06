from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sales/", views.sales, name="sales"),
    path("sales/wood-stamps/", views.wood_stamp_sales, name="wood_stamp_sales"),
    path("sales/<int:pk>/", views.sale_detail, name="sale_detail"),
    path("sales/<int:pk>/edit/", views.sale_edit, name="sale_edit"),
    path("sales/<int:pk>/delete/", views.sale_delete, name="sale_delete"),
    path("inventory/", views.inventory, name="inventory"),
    path("products/", views.products, name="products"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/toggle/", views.product_toggle, name="product_toggle"),
    path("products/<int:pk>/history/", views.product_history, name="product_history"),
    path("suppliers/", views.suppliers, name="suppliers"),
    path("reports/", views.reports, name="reports"),
    path("settings/", views.settings_page, name="settings"),
    path("settings/users/add/", views.add_user, name="add_user"),
    path("settings/users/<int:pk>/switch/", views.switch_user, name="switch_user"),
    path("backup/", views.backup, name="backup"),
    path("reset-sample/", views.reset_sample, name="reset_sample"),
]
