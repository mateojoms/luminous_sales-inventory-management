from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import Product, Supplier, User

class SignInForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Password"}))

class ProductForm(forms.ModelForm):
    supplier_text = forms.CharField(required=False, label="Supplier")
    class Meta:
        model = Product
        fields = ["name", "category", "description", "type", "color", "size_volume", "cost_price", "selling_price", "current_stock", "minimum_stock", "active", "track_stock"]
        labels = {"size_volume": "Size/volume", "cost_price": "Cost price", "selling_price": "Selling price", "current_stock": "Current quantity", "minimum_stock": "Minimum stock level", "track_stock": "Track stock"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier_text"].initial = self.instance.supplier_name

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "phone", "email", "address", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "role"]
        labels = {"username": "Username", "first_name": "First name", "last_name": "Last name"}
