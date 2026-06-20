from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class FleetMaintenance(models.Model):
    PURCHASE_STATUS_CHOICES = [
        ('CASH', 'Cash'),
        ('CREDIT', 'Credit'),
    ]
    PROJECT_CHOICES = [
        ('CADDELL', 'Caddell'),
        ('ADHOC', 'Adhoc'),
    ]

    date = models.DateField()
    truck_number_plate = models.CharField(max_length=50)
    item_needed = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    vat = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    vat_wth = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    amount_at_net = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    purchase_status = models.CharField(max_length=10, choices=PURCHASE_STATUS_CHOICES, default='CASH')
    project = models.CharField(max_length=10, choices=PROJECT_CHOICES, default='CADDELL')
    cost_percentage = models.FloatField(blank=True, null=True)
    quantity_stocked = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    quantity_released = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    quantity_stocked = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    quantity_released = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    total_remaining_items = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    total_cost_remaining = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = 'Fleet Maintenance Record'
        verbose_name_plural = 'Fleet Maintenance Records'

    def __str__(self):
        return f"{self.date} | {self.truck_number_plate} | {self.item_needed}"

    def compute_fields(self):
        qty = self.quantity if self.quantity is not None else Decimal('0')
        uc = self.unit_cost if self.unit_cost is not None else Decimal('0')
        self.amount = qty * uc

        vat = self.vat if self.vat is not None else Decimal('0')
        vat_wth = self.vat_wth if self.vat_wth is not None else Decimal('0')
        self.amount_at_net = self.amount + vat - vat_wth

        qty_stocked = self.quantity_stocked if self.quantity_stocked is not None else Decimal('0')
        qty_released = self.quantity_released if self.quantity_released is not None else Decimal('0')
        self.total_remaining_items = qty_stocked - qty_released
        self.total_cost_remaining = self.total_remaining_items * uc

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity < 0:
            raise ValidationError({'quantity': 'Quantity must be a non-negative number.'})
        if self.unit_cost is not None and self.unit_cost < 0:
            raise ValidationError({'unit_cost': 'Unit cost must be a non-negative number.'})
        if self.quantity_stocked is not None and self.quantity_stocked < 0:
            raise ValidationError({'quantity_stocked': 'Quantity stocked must be a non-negative number.'})
        if self.quantity_released is not None and self.quantity_released < 0:
            raise ValidationError({'quantity_released': 'Quantity released must be a non-negative number.'})
        self.compute_fields()

    def save(self, *args, **kwargs):
        self.compute_fields()
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.pk,
            'date': self.date.isoformat() if self.date else None,
            'truck_number_plate': self.truck_number_plate,
            'item_needed': self.item_needed,
            'quantity': str(self.quantity),
            'unit_cost': str(self.unit_cost),
            'amount': str(self.amount) if self.amount is not None else '0.00',
            'vat': str(self.vat),
            'vat_wth': str(self.vat_wth) if self.vat_wth is not None else '0.00',
            'amount_at_net': str(self.amount_at_net) if self.amount_at_net is not None else '0.00',
            'purchase_status': self.purchase_status,
            'purchase_status_display': self.get_purchase_status_display(),
            'project': self.project,
            'project_display': self.get_project_display(),
            'cost_percentage': self.cost_percentage,
            'quantity_stocked': str(self.quantity_stocked),
            'quantity_released': str(self.quantity_released),
            'total_remaining_items': str(self.total_remaining_items),
            'total_cost_remaining': str(self.total_cost_remaining),
        }


class SpareRelease(models.Model):
    date = models.DateField()
    truck_number_plate = models.CharField(max_length=50)
    item_released = models.CharField(max_length=255)
    quantity_released = models.DecimalField(max_digits=12, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    vat = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    vat_wth = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    amount_at_net = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    purchase_status = models.CharField(max_length=10, choices=FleetMaintenance.PURCHASE_STATUS_CHOICES, default='CASH')
    project = models.CharField(max_length=10, choices=FleetMaintenance.PROJECT_CHOICES, default='CADDELL')
    cost_percentage = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = 'Spare / Maintenance Item Release'
        verbose_name_plural = 'Spare / Maintenance Item Releases'

    def __str__(self):
        return f"{self.date} | {self.truck_number_plate} | {self.item_released}"

    def compute_fields(self):
        qty = self.quantity_released if self.quantity_released is not None else Decimal('0')
        uc = self.unit_cost if self.unit_cost is not None else Decimal('0')
        self.amount = qty * uc

        vat = self.vat if self.vat is not None else Decimal('0')
        vat_wth = self.vat_wth if self.vat_wth is not None else Decimal('0')
        self.amount_at_net = self.amount + vat - vat_wth

    def clean(self):
        super().clean()
        if self.quantity_released is not None and self.quantity_released < 0:
            raise ValidationError({'quantity_released': 'Quantity must be a non-negative number.'})
        if self.unit_cost is not None and self.unit_cost < 0:
            raise ValidationError({'unit_cost': 'Unit cost must be a non-negative number.'})
        self.compute_fields()

    def save(self, *args, **kwargs):
        self.compute_fields()
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.pk,
            'date': self.date.isoformat() if self.date else None,
            'truck_number_plate': self.truck_number_plate,
            'item_released': self.item_released,
            'quantity_released': str(self.quantity_released),
            'unit_cost': str(self.unit_cost),
            'amount': str(self.amount) if self.amount is not None else '0.00',
            'vat': str(self.vat),
            'vat_wth': str(self.vat_wth) if self.vat_wth is not None else '0.00',
            'amount_at_net': str(self.amount_at_net) if self.amount_at_net is not None else '0.00',
            'purchase_status': self.purchase_status,
            'purchase_status_display': self.get_purchase_status_display(),
            'project': self.project,
            'project_display': self.get_project_display(),
            'cost_percentage': self.cost_percentage,
        }