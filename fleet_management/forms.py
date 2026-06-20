from django import forms
from .models import FleetMaintenance, SpareRelease


class FleetMaintenanceForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-sm',
        })
    )
    truck_number_plate = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'e.g. UBB 143V',
        })
    )
    item_needed = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'e.g. Brake relay valve',
        })
    )
    quantity = forms.DecimalField(
        max_digits=12,
        decimal_places=4,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'step': '0.0001',
            'min': '0',
        })
    )
    unit_cost = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'step': '0.01',
            'min': '0',
        })
    )
    vat = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'step': '0.01',
            'min': '0',
        })
    )
    vat_wth = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'step': '0.01',
            'min': '0',
        })
    )
    purchase_status = forms.ChoiceField(
        choices=FleetMaintenance.PURCHASE_STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
        })
    )
    project = forms.ChoiceField(
        choices=FleetMaintenance.PROJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
        })
    )
    cost_percentage = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'step': '0.01',
            'min': '0',
            'max': '100',
            'placeholder': '% cost',
        })
    )

    class Meta:
        model = FleetMaintenance
        fields = [
            'date', 'truck_number_plate', 'item_needed',
            'quantity', 'unit_cost', 'vat', 'vat_wth',
            'purchase_status', 'project', 'cost_percentage',
            'quantity_stocked', 'quantity_released',
        ]
        # amount and amount_at_net are computed, not part of user input

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('vat') is None:
            from decimal import Decimal
            cleaned['vat'] = Decimal('0.00')
        return cleaned


class FleetCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control form-control-sm',
            'accept': '.csv',
        })
    )
    skip_rows = forms.IntegerField(
        label='Skip header rows',
        initial=1,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
        })
    )


class SpareReleaseForm(forms.ModelForm):
    class Meta:
        model = SpareRelease
        fields = [
            'date', 'truck_number_plate', 'item_released',
            'quantity_released', 'unit_cost', 'vat', 'vat_wth',
            'purchase_status', 'project', 'cost_percentage',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'truck_number_plate': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. UBB 143V'}),
            'item_released': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. Spare tire'}),
            'quantity_released': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001', 'min': '0'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'}),
            'vat': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0', 'initial': '0'}),
            'vat_wth': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'}),
            'purchase_status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'project': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'cost_percentage': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0', 'max': '100'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('vat') is None:
            from decimal import Decimal
            cleaned['vat'] = Decimal('0.00')
        return cleaned