import csv
import io
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse
from .forms import CsvImportForm, StoreTransactionForm
from .models import Product, StoreTransaction


# ── Helpers ──────────────────────────────────────────────────────────────────

def _clean_decimal(raw):
    """Strip whitespace, commas, and common currency symbols; return Decimal or None."""
    if raw is None:
        return None
    cleaned = str(raw).strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _aggregate(qs):
    """Build financial summaries and Chart.js-ready structures from a queryset."""
    total_value_stocked = Decimal("0")
    total_cost_remaining = Decimal("0")
    total_cash = Decimal("0")
    total_credit = Decimal("0")

    chart_labels = []
    chart_stocked = []
    chart_released = []

    # New: daily expenditure tracking and top 5 expenditures
    daily_expenditure = defaultdict(Decimal)
    product_expenditure = defaultdict(Decimal)

    for t in qs:
        total_value_stocked += t.total_amount_stocked or Decimal("0")
        total_cost_remaining += t.total_cost_remaining
        if t.purchase_status == "CASH":
            total_cash += t.total_amount_stocked or Decimal("0")
            total_value_stocked += t.quantity_stocked
        else:
            total_credit += t.total_amount_stocked or Decimal("0")

        chart_labels.append(t.product.name)
        chart_stocked.append(float(t.quantity_stocked or 0))
        chart_released.append(float(t.quantity_released or 0))

        # Track daily expenditure
        date_key = t.date.isoformat() if t.date else "Unknown"
        daily_expenditure[date_key] += t.total_amount_stocked or Decimal("0")

        # Track product expenditure for top 5
        product_expenditure[t.product.name] += t.total_amount_stocked or Decimal("0")

    # Build daily expenditure chart data (sorted by date)
    sorted_dates = sorted(daily_expenditure.keys())
    daily_labels = sorted_dates
    daily_data = [float(daily_expenditure[d]) for d in sorted_dates]

    # Build top 5 expenditures
    top_5_expenditures = sorted(
        product_expenditure.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return {
        "summary": {
            "total_value_stocked": float(total_value_stocked),
            "total_cost_remaining": float(total_cost_remaining),
            "total_cash": float(total_cash),
            "total_credit": float(total_credit),
        },
        "charts": {
            "bar": {
                "labels": chart_labels,
                "stocked": chart_stocked,
                "released": chart_released,
            },
            "doughnut": {
                "labels": ["Cash", "Credit"],
                "values": [float(total_cash), float(total_credit)],
            },
            "daily_expenditure": {
                "labels": daily_labels,
                "data": daily_data,
            },
            "top_expenditures": [
                {"product": name, "amount": float(amount)}
                for name, amount in top_5_expenditures
            ],
        },
    }


def _get_or_create_product(name):
    """Return a Product instance, creating it if it doesn't exist yet."""
    name = name.strip()
    if not name:
        return None
    product, _ = Product.objects.get_or_create(name=name)
    return product


# ── Views ─────────────────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    """Render the single-page dashboard shell."""
    form = StoreTransactionForm()
    csv_form = CsvImportForm()
    today = datetime.today().strftime("%Y-%m")

    # Keeping this INSIDE the function dynamically fetches
    # the URLs only when the page is requested.
    urls = {
        "data": reverse("store_management:fetch_monthly_data"),
        "add": reverse("store_management:add_transaction"),
        "import": reverse("store_management:import_csv"),
        "products": reverse("store_management:product_list"),
        "create_product": reverse("store_management:create_product"),
    }

    return render(
        request,
        "store_management/dashboard.html",
        {"form": form, "csv_form": csv_form, "current_period": today, "urls": urls},
    )


@login_required
@require_GET
def fetch_monthly_data_api(request):
    """GET /api/data/?period=YYYY-MM — returns products (with nested transactions) + aggregates."""
    period = request.GET.get("period", "")
    try:
        year, month = [int(x) for x in period.split("-")]
    except (ValueError, AttributeError):
        return JsonResponse({"error": "Invalid period. Expected YYYY-MM."}, status=400)

    # Transactions for the selected month
    qs = StoreTransaction.objects.filter(date__year=year, date__month=month).select_related("product")
    
    # Build aggregates across ALL transactions in the month
    aggregates = _aggregate(qs)
    # Group transactions by product for the expandable UI
    products_map = {}
    for t in qs:
        pid = t.product_id
        if pid not in products_map:
            products_map[pid] = {
                "product": {
                    "id": pid,
                    "name": t.product.name,
                },
                "transactions": [],
                "_totals": {
                    "total_stocked": Decimal("0"),
                    "total_released": Decimal("0"),
                    "total_amount": Decimal("0"),
                },
            }
        products_map[pid]["transactions"].append(t.to_json())
        products_map[pid]["_totals"]["total_stocked"] += t.quantity_stocked or Decimal("0")
        products_map[pid]["_totals"]["total_released"] += t.quantity_released or Decimal("0")
        products_map[pid]["_totals"]["total_amount"] += t.total_amount_stocked or Decimal("0")

    products_data = []
    for pid in sorted(products_map.keys()):
        entry = products_map[pid]
        products_data.append({
            "product": entry["product"],
            "transactions": entry["transactions"],
            "totals": {
                "total_stocked": float(entry["_totals"]["total_stocked"]),
                "total_released": float(entry["_totals"]["total_released"]),
                "total_amount": float(entry["_totals"]["total_amount"]),
            },
        })

    return JsonResponse(
        {
            "products": products_data,
            **aggregates,
        }
    )


@login_required
@require_GET
def product_list_api(request):
    """GET /api/products/ — return all products as JSON for the typeahead/select."""
    products = Product.objects.all().values("id", "name").order_by("name")
    return JsonResponse({"products": list(products)})


@login_required
@require_POST
def create_product_ajax(request):
    """POST /api/products/create/ — create a new product, return JSON."""
    import json
    try:
        data = json.loads(request.body) if request.body else request.POST
        name = data.get("name", "").strip()
    except Exception:
        name = request.POST.get("name", "").strip()

    if not name:
        return JsonResponse({"success": False, "errors": {"name": "Product name is required."}}, status=400)

    product, created = Product.objects.get_or_create(name=name)
    return JsonResponse({
        "success": True,
        "created": created,
        "product": {"id": product.id, "name": product.name},
    })


@login_required
@require_POST
def add_transaction_ajax(request):
    """POST /api/add/ — validate + save a single transaction, return JSON."""
    form = StoreTransactionForm(request.POST)
    if form.is_valid():
        transaction = form.save()
        return JsonResponse({"success": True, "transaction": transaction.to_json()}, status=201)

    return JsonResponse({"success": False, "errors": form.errors}, status=400)


@login_required
@require_POST
def edit_transaction_ajax(request, pk):
    """POST /api/edit/<pk>/ — update an existing transaction, return JSON."""
    try:
        transaction = StoreTransaction.objects.get(pk=pk)
    except StoreTransaction.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    form = StoreTransactionForm(request.POST, instance=transaction)
    if form.is_valid():
        updated = form.save()
        return JsonResponse({"success": True, "transaction": updated.to_json()})

    return JsonResponse({"success": False, "errors": form.errors}, status=400)


@login_required
@require_POST
def delete_transaction_ajax(request, pk):
    """POST /api/delete/<pk>/ — delete a transaction, return JSON."""
    try:
        transaction = StoreTransaction.objects.get(pk=pk)
        transaction.delete()
        return JsonResponse({"success": True})
    except StoreTransaction.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)


@login_required
@require_POST
def stock_item_ajax(request):
    """POST /api/stock/ — add to existing transaction on the same master product."""
    product_id = request.POST.get('product')
    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "errors": {"product": "Product is required."}}, status=400)

    try:
        add_qty = Decimal(request.POST.get('quantity_stocked', '0'))
    except InvalidOperation:
        return JsonResponse({"success": False, "errors": {"quantity_stocked": "Invalid quantity."}}, status=400)

    if add_qty <= 0:
        return JsonResponse({"success": False, "errors": {"quantity_stocked": "Quantity must be greater than 0."}}, status=400)

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "errors": {"product": "Product not found."}}, status=404)

    # Find an existing transaction for this product to update
    existing = StoreTransaction.objects.filter(product=product).first()

    if not existing:
        # No existing transaction, create new one
        form_data = request.POST.copy()
        form_data['quantity_released'] = 0
        form = StoreTransactionForm(form_data)
        if form.is_valid():
            transaction = form.save()
            return JsonResponse({"success": True, "transaction": transaction.to_json()}, status=201)
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    # Update existing transaction - add to stocked quantity
    existing.quantity_stocked = (existing.quantity_stocked or Decimal("0")) + add_qty
    # Recalculate total_amount_stocked
    unit = existing.unit_price or Decimal("0")
    vat = existing.vat or Decimal("0")
    existing.total_amount_stocked = existing.quantity_stocked * (unit + vat)
    existing.save()

    return JsonResponse({"success": True, "transaction": existing.to_json(), "updated": True})


@login_required
@require_POST
def release_item_ajax(request):
    """POST /api/release/ — deduct from existing transaction on the same master product."""
    product_id = request.POST.get('product')
    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "errors": {"product": "Product is required."}}, status=400)

    try:
        release_qty = Decimal(request.POST.get('quantity_released', '0'))
    except InvalidOperation:
        return JsonResponse({"success": False, "errors": {"quantity_released": "Invalid quantity."}}, status=400)

    if release_qty <= 0:
        return JsonResponse({"success": False, "errors": {"quantity_released": "Quantity must be greater than 0."}}, status=400)

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "errors": {"product": "Product not found."}}, status=404)

    # Find an existing transaction for this product with remaining stock
    existing = StoreTransaction.objects.filter(
        product=product,
        quantity_stocked__gt=0
    ).order_by('date').first()

    if not existing:
        return JsonResponse({"success": False, "errors": {"quantity_released": "No stocked inventory found for this product."}}, status=400)

    existing.quantity_released = (existing.quantity_released or Decimal("0")) + release_qty
    existing.save()

    return JsonResponse({"success": True, "transaction": existing.to_json(), "updated": True})


@login_required
@require_POST
def import_csv_ajax(request):
    """POST /api/import/ — parse uploaded CSV, auto-create products, bulk-create transactions."""
    csv_form = CsvImportForm(request.POST, request.FILES)
    if not csv_form.is_valid():
        return JsonResponse({"success": False, "errors": csv_form.errors}, status=400)

    csv_file = request.FILES["csv_file"]
    decoded = csv_file.read().decode("utf-8-sig")  # handle BOM
    reader = csv.reader(io.StringIO(decoded))

    created_rows = []
    errors = []

    # Skip header row if it looks like a header
    rows = list(reader)
    start_index = 0
    if rows and not _clean_decimal(rows[0][0] if rows[0] else None):
        # First cell is not a date-parseable decimal — assume it's a header
        start_index = 1

    for i, row in enumerate(rows[start_index:], start=start_index + 1):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows

        try:
            # Pad short rows
            while len(row) < 9:
                row.append("")

            raw_date = row[0].strip()
            item_name = row[1].strip()
            qty_stocked = _clean_decimal(row[2])
            available = _clean_decimal(row[3])
            unit_price = _clean_decimal(row[4])
            vat_raw = _clean_decimal(row[5])
            total_amount_raw = _clean_decimal(row[6])
            qty_released = _clean_decimal(row[7])
            status_raw = row[8].strip().upper() if len(row) > 8 else "Cash"
            purchase_status = status_raw if status_raw in ("Cash", "Credit") else "Cash"

            # Parse date (accept multiple common formats)
            date_obj = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                try:
                    date_obj = datetime.strptime(raw_date, fmt).date()
                    break
                except ValueError:
                    continue

            if not date_obj:
                errors.append({"row": i, "error": f"Unparseable date: '{raw_date}'"})
                continue

            if not item_name:
                errors.append({"row": i, "error": "Item name is required."})
                continue

            if qty_stocked is None:
                errors.append({"row": i, "error": "Quantity stocked is required."})
                continue

            if unit_price is None:
                errors.append({"row": i, "error": "Unit price is required."})
                continue

            # Auto-create or retrieve the product
            product = _get_or_create_product(item_name)

            obj = StoreTransaction(
                date=date_obj,
                product=product,
                quantity_stocked=qty_stocked,
                available_items=available,
                unit_price=unit_price,
                vat=vat_raw,                      # None → model will calculate
                total_amount_stocked=total_amount_raw,  # None → model will calculate
                quantity_released=qty_released or Decimal("0"),
                purchase_status=purchase_status,
            )
            obj.save()
            created_rows.append(obj.to_json())

        except Exception as exc:  # noqa: BLE001
            errors.append({"row": i, "error": str(exc)})

    return JsonResponse(
        {
            "success": True,
            "created": len(created_rows),
            "errors": errors,
            "transactions": created_rows,
        },
        status=201 if created_rows else 200,
    )