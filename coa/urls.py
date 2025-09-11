from django.urls import path
from . import views

app_name = "coa"

urlpatterns = [
    # Chart of Accounts
    path("", views.chart_of_accounts_view, name="chart_of_accounts"),
    path("account/<int:account_id>/", views.account_detail_view, name="account_detail"),
    path("account/create/", views.create_account_view, name="create_account"),
    path("api/account-search/", views.account_search_api, name="account_search_api"),
    # Tax Rates
    path("tax-rates/", views.tax_rate_list_view, name="tax_rates"),
    path("tax-rates/new/", views.tax_rate_create_view, name="tax_rate_new"),
    path(
        "tax-rates/<int:tax_rate_id>/edit/",
        views.tax_rate_update_view,
        name="tax_rate_edit",
    ),
    path(
        "tax-rates/<int:tax_rate_id>/delete/",
        views.tax_rate_delete_view,
        name="tax_rate_delete",
    ),
    path(
        "api/tax-rates/create/", views.tax_rate_api_create, name="tax_rate_api_create"
    ),
]
