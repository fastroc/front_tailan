from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    path('', views.assets_list, name='list'),
    path('new/', views.new_asset, name='new'),
    path('<int:asset_id>/', views.asset_detail, name='detail'),
    path('<int:asset_id>/edit/', views.edit_asset, name='edit'),
    path('<int:asset_id>/depreciation/', views.asset_depreciation, name='depreciation'),
    path('run-depreciation/', views.run_depreciation, name='run_depreciation'),
    path('import/', views.import_assets, name='import'),
    path('export/', views.export_assets, name='export'),
]
