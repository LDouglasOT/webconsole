from django.urls import path
from . import views

app_name = 'fleet_management'

urlpatterns = [
    path('', views.fleet_dashboard_view, name='dashboard'),
    path('api/fetch/', views.fetch_fleet_data_api, name='fetch_fleet_data'),
    path('api/add/', views.add_maintenance_ajax, name='add_maintenance'),
    path('api/edit/<int:pk>/', views.edit_maintenance_ajax, name='edit_maintenance'),
    path('api/delete/<int:pk>/', views.delete_maintenance_ajax, name='delete_maintenance'),
    path('api/stock/', views.stock_item_ajax, name='stock_item'),
    path('api/release/', views.release_item_ajax, name='release_item'),
    path('api/import-csv/', views.import_fleet_csv_ajax, name='import_csv'),
    path('api/spare/add/', views.add_spare_release_ajax, name='add_spare_release'),
    path('api/spare/fetch/', views.fetch_spare_releases_api, name='fetch_spare_releases'),
    path('api/spare/daily/', views.fetch_spare_daily_expenditure_api, name='fetch_spare_daily'),
]