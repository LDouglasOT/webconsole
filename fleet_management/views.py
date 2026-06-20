import csv
import io
import json
from collections import defaultdict
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.db.models import Sum, Q

from .forms import FleetCsvImportForm, FleetMaintenanceForm, SpareReleaseForm
from .models import FleetMaintenance, SpareRelease


def _build_urls():
    """Return a dict of named URLs for use inside the SPA template."""
    return {
        'dashboard': reverse('fleet_management:dashboard'),
        'fetch_fleet_data': reverse('fleet_management:fetch_fleet_data'),
        'add_maintenance': reverse('fleet_management:add_maintenance'),
        'stock_item': reverse('fleet_management:stock_item'),
        'release_item': reverse('fleet_management:release_item'),
        'import_csv': reverse('fleet_management:import_csv'),
        'add_spare_release': reverse('fleet_management:add_spare_release'),
        'fetch_spare_releases': reverse('fleet_management:fetch_spare_releases'),
        'fetch_spare_daily': reverse('fleet_management:fetch_spare_daily'),
        'edit_maintenance': reverse('fleet_management:edit_maintenance', kwargs={'pk': 0}),
        'delete_maintenance': reverse('fleet_management:delete_maintenance', kwargs={'pk': 0}),
    }


def _safe_decimal(value, default=Decimal('0.00')):
    """Convert a value to Decimal safely."""
    if value in (None, '', 'None'):
        return default
    try:
        return Decimal(str(value).strip())
    except InvalidOperation:
        return default


# ---------------------------------------------------------------------------
# Dashboard shell
# ---------------------------------------------------------------------------

@login_required
def fleet_dashboard_view(request):
    today = date.today()
    current_period = today.strftime('%Y-%m')

    context = {
        'form': FleetMaintenanceForm(),
        'spare_form': SpareReleaseForm(),
        'csv_form': FleetCsvImportForm(),
        'current_period': current_period,
        'urls': _build_urls(),
        'purchase_status_choices': FleetMaintenance.PURCHASE_STATUS_CHOICES,
        'project_choices': FleetMaintenance.PROJECT_CHOICES,
    }
    return render(request, 'fleet_management/dashboard.html', context)


# ---------------------------------------------------------------------------
# Data API
# ---------------------------------------------------------------------------

@login_required
def fetch_fleet_data_api(request):
    period = request.GET.get('period', '')
    search = request.GET.get('search', '').strip()

    qs = FleetMaintenance.objects.all()

    if period:
        try:
            year, month = [int(x) for x in period.split('-')]
            qs = qs.filter(date__year=year, date__month=month)
        except (ValueError, AttributeError):
            pass

    if search:
        qs = qs.filter(
            Q(item_needed__icontains=search) |
            Q(truck_number_plate__icontains=search)
        )

    records = list(qs)

    daily_expenditure = defaultdict(Decimal)
    for r in records:
        date_key = r.date.isoformat() if r.date else 'Unknown'
        daily_expenditure[date_key] += (r.amount or Decimal('0'))

    sorted_dates = sorted(daily_expenditure.keys())
    daily_labels = sorted_dates
    daily_data = [float(daily_expenditure[d]) for d in sorted_dates]

    item_totals = defaultdict(Decimal)
    for r in records:
        item_totals[r.item_needed] += (r.amount or Decimal('0'))
    top_items = sorted(item_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    truck_totals = defaultdict(Decimal)
    for r in records:
        truck_totals[r.truck_number_plate] += (r.amount or Decimal('0'))

    project_totals = defaultdict(Decimal)
    for r in records:
        project_totals[r.get_project_display()] += (r.amount or Decimal('0'))

    total_amount = sum((r.amount or Decimal('0')) for r in records)
    total_net = sum((r.amount_at_net or Decimal('0')) for r in records)
    total_cash = sum((r.amount or Decimal('0')) for r in records if r.purchase_status == 'CASH')
    total_credit = sum((r.amount or Decimal('0')) for r in records if r.purchase_status == 'CREDIT')

    payload = {
        'records': [r.to_dict() for r in records],
        'kpi': {
            'total_amount': float(total_amount),
            'total_net': float(total_net),
            'total_cash': float(total_cash),
            'total_credit': float(total_credit),
            'record_count': len(records),
            'total_stocked': float(sum((r.quantity_stocked or Decimal('0')) for r in records)),
            'total_released': float(sum((r.quantity_released or Decimal('0')) for r in records)),
            'total_remaining': float(sum((r.total_remaining_items or Decimal('0')) for r in records)),
        },
        'charts': {
            'bar': {
                'labels': [i[0] for i in top_items],
                'data': [float(i[1]) for i in top_items],
            },
            'project_doughnut': {
                'labels': list(project_totals.keys()),
                'data': [float(v) for v in project_totals.values()],
            },
            'truck_doughnut': {
                'labels': list(truck_totals.keys()),
                'data': [float(v) for v in truck_totals.values()],
            },
            'daily_expenditure': {
                'labels': daily_labels,
                'data': daily_data,
            },
            'purchase_status_pct': {
                'labels': ['Cash', 'Credit'],
                'data': [
                    float(total_cash / total_amount * 100) if total_amount > 0 else 0,
                    float(total_credit / total_amount * 100) if total_amount > 0 else 0,
                ],
            },
        },
    }
    return JsonResponse(payload)


# ---------------------------------------------------------------------------
# Add / Edit / Delete
# ---------------------------------------------------------------------------

@login_required
@require_POST
def add_maintenance_ajax(request):
    form = FleetMaintenanceForm(request.POST)
    if form.is_valid():
        record = form.save()
        return JsonResponse({'success': True, 'record': record.to_dict()})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_http_methods(['GET', 'POST'])
def edit_maintenance_ajax(request, pk):
    record = get_object_or_404(FleetMaintenance, pk=pk)

    if request.method == 'GET':
        return JsonResponse({'success': True, 'record': record.to_dict()})

    form = FleetMaintenanceForm(request.POST, instance=record)
    if form.is_valid():
        updated = form.save()
        return JsonResponse({'success': True, 'record': updated.to_dict()})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def delete_maintenance_ajax(request, pk):
    record = get_object_or_404(FleetMaintenance, pk=pk)
    record.delete()
    return JsonResponse({'success': True, 'id': pk})


# ---------------------------------------------------------------------------
# Stock operations
# ---------------------------------------------------------------------------

@login_required
@require_POST
def stock_item_ajax(request):
    truck_number_plate = request.POST.get('truck_number_plate')
    item_needed = request.POST.get('item_needed')
    try:
        qty = Decimal(request.POST.get('quantity_stocked', '0'))
        unit_cost = Decimal(request.POST.get('unit_cost', '0'))
    except InvalidOperation:
        return JsonResponse({'success': False, 'errors': {'quantity_stocked': 'Invalid quantity.'}}, status=400)

    if qty <= 0:
        return JsonResponse({'success': False, 'errors': {'quantity_stocked': 'Quantity must be greater than 0.'}}, status=400)

    existing = FleetMaintenance.objects.filter(truck_number_plate=truck_number_plate, item_needed=item_needed).first()

    if not existing:
        date_val = request.POST.get('date') or date.today().isoformat()
        record = FleetMaintenance(
            date=date_val,
            truck_number_plate=truck_number_plate,
            item_needed=item_needed,
            quantity_stocked=qty,
            quantity_released=Decimal('0'),
            unit_cost=unit_cost,
            purchase_status=request.POST.get('purchase_status', 'CASH'),
            project=request.POST.get('project', 'CADDELL'),
        )
        record.save()
        return JsonResponse({'success': True, 'record': record.to_dict()})

    existing.quantity_stocked = (existing.quantity_stocked or Decimal('0')) + qty
    existing.unit_cost = unit_cost
    existing.save()
    return JsonResponse({'success': True, 'record': existing.to_dict(), 'updated': True})


@login_required
@require_POST
def release_item_ajax(request):
    truck_number_plate = request.POST.get('truck_number_plate')
    item_needed = request.POST.get('item_needed')
    try:
        qty = Decimal(request.POST.get('quantity_released', '0'))
    except InvalidOperation:
        return JsonResponse({'success': False, 'errors': {'quantity_released': 'Invalid quantity.'}}, status=400)

    if qty <= 0:
        return JsonResponse({'success': False, 'errors': {'quantity_released': 'Quantity must be greater than 0.'}}, status=400)

    existing = FleetMaintenance.objects.filter(
        truck_number_plate=truck_number_plate,
        item_needed=item_needed,
        quantity_stocked__gt=0
    ).order_by('date').first()

    if not existing:
        return JsonResponse({'success': False, 'errors': {'quantity_released': 'No stocked inventory found for this item.'}}, status=400)

    remaining = (existing.quantity_stocked or Decimal('0')) - (existing.quantity_released or Decimal('0'))
    if qty > remaining:
        return JsonResponse({'success': False, 'errors': {'quantity_released': f'Insufficient stock. Only {remaining} remaining.'}}, status=400)

    existing.quantity_released = (existing.quantity_released or Decimal('0')) + qty
    existing.save()
    return JsonResponse({'success': True, 'record': existing.to_dict(), 'updated': True})


# ---------------------------------------------------------------------------
# Spare / Maintenance Item Releases
# ---------------------------------------------------------------------------

@login_required
@require_POST
def add_spare_release_ajax(request):
    form = SpareReleaseForm(request.POST)
    if form.is_valid():
        record = form.save()
        return JsonResponse({'success': True, 'record': record.to_dict()})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_GET
def fetch_spare_releases_api(request):
    period = request.GET.get('period', '')
    records = SpareRelease.objects.all()
    if period:
        try:
            year, month = [int(x) for x in period.split('-')]
            records = records.filter(date__year=year, date__month=month)
        except (ValueError, AttributeError):
            pass
    return JsonResponse({'records': [r.to_dict() for r in records]})


@login_required
@require_GET
def fetch_spare_daily_expenditure_api(request):
    period = request.GET.get('period', '')
    qs = SpareRelease.objects.all()
    if period:
        try:
            year, month = [int(x) for x in period.split('-')]
            qs = qs.filter(date__year=year, date__month=month)
        except (ValueError, AttributeError):
            pass
    daily = defaultdict(float)
    for r in qs:
        key = r.date.isoformat()
        daily[key] += float(r.amount_at_net or r.amount or 0)
    return JsonResponse({'daily': [{'date': k, 'amount': v} for k, v in sorted(daily.items())]})


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

@login_required
@require_POST
def import_fleet_csv_ajax(request):
    form = FleetCsvImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    csv_file = request.FILES['csv_file']
    skip_rows = form.cleaned_data.get('skip_rows') or 1

    try:
        raw = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        raw = csv_file.read().decode('latin-1')

    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)

    data_rows = []
    skipped = 0
    for row in rows:
        non_empty = [c.strip() for c in row if c.strip()]
        if not non_empty:
            continue
        if skipped < skip_rows:
            skipped += 1
            continue
        data_rows.append(row)

    created_count = 0
    errors = []

    for i, row in enumerate(data_rows, start=1):
        if not any(c.strip() for c in row):
            continue

        def cell(idx, default=''):
            try:
                return row[idx].strip() if row[idx].strip() else default
            except IndexError:
                return default

        raw_date = cell(0)
        if not raw_date:
            errors.append(f'Row {i}: missing date, skipped.')
            continue

        parsed_date = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                continue
        if parsed_date is None:
            errors.append(f'Row {i}: unrecognised date format "{raw_date}", skipped.')
            continue

        truck = cell(1)
        item = cell(2)
        if not truck or not item:
            errors.append(f'Row {i}: missing truck or item, skipped.')
            continue

        quantity = _safe_decimal(cell(3, '1'))
        unit_cost = _safe_decimal(cell(4, '0'))
        vat = _safe_decimal(cell(5, '0'))
        vat_wth_val = cell(6, None)
        vat_wth = _safe_decimal(vat_wth_val) if vat_wth_val not in (None, '', 'None') else None

        ps_raw = cell(7, 'CASH').upper()
        purchase_status = ps_raw if ps_raw in ('CASH', 'CREDIT') else 'CASH'

        proj_raw = cell(8, 'ADHOC').upper()
        project = proj_raw if proj_raw in ('CADDELL', 'ADHOC') else 'ADHOC'

        cp_raw = cell(9, None)
        cost_percentage = None
        if cp_raw:
            try:
                cost_percentage = float(cp_raw.replace('%', ''))
            except ValueError:
                pass

        quantity_stocked = _safe_decimal(cell(10, '0'))
        quantity_released = _safe_decimal(cell(11, '0'))

        try:
            record = FleetMaintenance(
                date=parsed_date,
                truck_number_plate=truck,
                item_needed=item,
                quantity=quantity,
                unit_cost=unit_cost,
                vat=vat,
                vat_wth=vat_wth,
                purchase_status=purchase_status,
                project=project,
                cost_percentage=cost_percentage,
                quantity_stocked=quantity_stocked,
                quantity_released=quantity_released,
            )
            record.save()
            created_count += 1
        except Exception as exc:
            errors.append(f'Row {i}: save error – {exc}')

    return JsonResponse({
        'success': True,
        'created': created_count,
        'errors': errors,
    })
