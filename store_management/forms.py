from django import forms
from .models import Product, StoreTransaction


class StoreTransactionForm(forms.ModelForm):
    """Manual entry form — replaces text-based item_name with a product FK."""

    class Meta:
        model = StoreTransaction
        # Exclude fields that are auto-calculated in the model's save()
        fields = [
            "date",
            "product",
            "quantity_stocked",
            "available_items",
            "unit_price",
            "vat",
            "total_amount_stocked",
            "quantity_released",
            "purchase_status",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "product": forms.Select(attrs={"class": "form-input"}),
            "quantity_stocked": forms.NumberInput(attrs={"class": "form-input", "step": "0.0001", "min": "0"}),
            "available_items": forms.NumberInput(attrs={"class": "form-input", "step": "0.0001", "min": "0"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-input", "step": "0.0001", "min": "0"}),
            "vat": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.0001", "min": "0", "placeholder": "Leave blank to auto-calculate (18%)"}
            ),
            "total_amount_stocked": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.0001", "min": "0", "placeholder": "Leave blank to auto-calculate"}
            ),
            "quantity_released": forms.NumberInput(attrs={"class": "form-input", "step": "0.0001", "min": "0"}),
            "purchase_status": forms.Select(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make auto-calculated fields optional in the form
        self.fields["vat"].required = False
        self.fields["total_amount_stocked"].required = False
        self.fields["available_items"].required = False
        # Order products alphabetically
        self.fields["product"].queryset = Product.objects.all().order_by("name")
        self.fields["product"].label = "Product / Item"
        self.fields["product"].empty_label = "--- Select or type to search ---"


class ProductForm(forms.ModelForm):
    """Quick-add form for creating a new product on the fly."""

    class Meta:
        model = Product
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "New product name…",
                "id": "newProductInput",
            }),
        }
        labels = {"name": "Product Name"}


class CsvImportForm(forms.Form):
    """Bulk upload form for CSV files."""

    csv_file = forms.FileField(
        label="CSV File",
        widget=forms.FileInput(
            attrs={
                "accept": ".csv",
                "class": "hidden",
                "id": "csv-file-input",
            }
        ),
        help_text=(
            "Expected columns (order matters): DATE, ITEM NAME, QUANTITY STOCKED, "
            "AVAILABLE ITEMS, UNIT PRICE, VAT, TOTAL AMOUNT STOCKED, "
            "QUANTITY RELEASED, PURCHASE STATUS"
        ),
    )