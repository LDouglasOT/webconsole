from django.db import models
from decimal import Decimal


class Product(models.Model):
    """Master product catalogue — each product is uniquely identified by name."""

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name


class StoreTransaction(models.Model):
    PURCHASE_STATUS_CHOICES = [
        ("CASH", "Cash"),
        ("CREDIT", "Credit"),
        ("RELEASE", "Release"),
    ]

    date = models.DateField()
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Product",
    )
    quantity_stocked = models.DecimalField(max_digits=14, decimal_places=4)
    available_items = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=14, decimal_places=4)
    vat = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    total_amount_stocked = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    quantity_released = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    purchase_status = models.CharField(max_length=10, choices=PURCHASE_STATUS_CHOICES, default="CASH")
    

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "product__name"]
        verbose_name = "Store Transaction"
        verbose_name_plural = "Store Transactions"

    def __str__(self):
        return f"{self.date} – {self.product.name}"

    def save(self, *args, **kwargs):
        # VAT fallback: calculate only if not explicitly provided
        if not self.vat:
            self.vat = (self.unit_price or Decimal("0")) * (Decimal("0.18") / Decimal("0.82"))

        # Total amount stocked fallback: calculate only if not explicitly provided
        if not self.total_amount_stocked:
            self.total_amount_stocked = (self.quantity_stocked or Decimal("0")) * (
                (self.unit_price or Decimal("0")) + (self.vat or Decimal("0"))
            )

        super().save(*args, **kwargs)

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def total_remaining_items(self):
        stocked = self.quantity_stocked or Decimal("0")
        released = self.quantity_released or Decimal("0")
        return stocked - released

    @property
    def total_cost_remaining(self):
        unit = self.unit_price or Decimal("0")
        vat = self.vat or Decimal("0")
        return self.total_remaining_items * (unit + vat)

    # ── AJAX serialisation ───────────────────────────────────────────────────

    def to_json(self):
        return {
            "id": self.pk,
            "date": self.date.isoformat() if self.date else None,
            "product_id": self.product_id,
            "product_name": self.product.name,
            "quantity_stocked": float(self.quantity_stocked or 0),
            "available_items": float(self.available_items or 0),
            "unit_price": float(self.unit_price or 0),
            "vat": float(self.vat or 0),
            "total_amount_stocked": float(self.total_amount_stocked or 0),
            "quantity_released": float(self.quantity_released or 0),
            "total_remaining_items": float(self.total_remaining_items),
            "purchase_status": self.purchase_status,
            "total_cost_remaining": float(self.total_cost_remaining),
        }