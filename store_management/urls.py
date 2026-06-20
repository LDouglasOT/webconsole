from django.urls import path
from . import views

app_name = "store_management"

urlpatterns = [
    # Dashboard (single-page shell)
    path("", views.dashboard_view, name="dashboard"),

    # AJAX data API
    path("api/data/", views.fetch_monthly_data_api, name="fetch_monthly_data"),
    path("api/products/", views.product_list_api, name="product_list"),
    path("api/add/", views.add_transaction_ajax, name="add_transaction"),
    path("api/stock/", views.stock_item_ajax, name="stock_item"),
    path("api/release/", views.release_item_ajax, name="release_item"),
    path("api/edit/<int:pk>/", views.edit_transaction_ajax, name="edit_transaction"),
    path("api/products/create/", views.create_product_ajax, name="create_product"),
    path("api/delete/<int:pk>/", views.delete_transaction_ajax, name="delete_transaction"),
    path("api/import/", views.import_csv_ajax, name="import_csv"),
]