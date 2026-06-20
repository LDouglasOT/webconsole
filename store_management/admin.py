from django.contrib import admin
from .models import Product, StoreTransaction


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "transaction_count", "created_at")
    search_fields = ("name",)
    ordering = ("name",)

    @admin.display(description="Transactions")
    def transaction_count(self, obj):
        return obj.transactions.count()


@admin.register(StoreTransaction)
class StoreTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "product_name",
        "quantity_stocked",
        "quantity_released",
        "total_remaining_items",
        "unit_price",
        "vat",
        "total_amount_stocked",
        "purchase_status",
        "total_cost_remaining",
    )
    list_filter = ("purchase_status", "date", "product")
    search_fields = ("product__name",)
    ordering = ("-date", "product__name")
    readonly_fields = ("total_remaining_items", "total_cost_remaining")

    fieldsets = (
        ("Core Details", {
            "fields": ("date", "product", "purchase_status")
        }),
        ("Quantities", {
            "fields": ("quantity_stocked", "available_items", "quantity_released")
        }),
        ("Pricing", {
            "fields": ("unit_price", "vat", "total_amount_stocked")
        }),
        ("Computed (read-only)", {
            "fields": ("total_remaining_items", "total_cost_remaining"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Item")
    def product_name(self, obj):
        return obj.product.name