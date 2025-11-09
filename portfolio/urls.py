from django.urls import path
from . import views

urlpatterns = [
    path('api/ticker-info/', views.ticker_info, name='api-ticker-info'),
    path('api/tickers/', views.list_tickers, name='api-tickers'),
    path("", views.PortfolioListView.as_view(), name="portfolio-list"),
    path("portfolio/new/", views.PortfolioCreateView.as_view(), name="portfolio-create"),
    path("portfolio/<int:pk>/", views.PortfolioDetailView.as_view(), name="portfolio-detail"),
    path("portfolio/<int:pk>/edit/", views.PortfolioUpdateView.as_view(), name="portfolio-edit"),
    path("portfolio/<int:pk>/delete/", views.PortfolioDeleteView.as_view(), name="portfolio-delete"),
    path("investment/new/", views.InvestmentCreateView.as_view(), name="investment-create"),
    path("investment/<int:pk>/edit/", views.InvestmentUpdateView.as_view(), name="investment-edit"),
    path("investment/<int:pk>/delete/", views.InvestmentDeleteView.as_view(), name="investment-delete"),
    path("investment/<int:investment_pk>/tx/new/", views.TransactionCreateView.as_view(), name="transaction-create"),
]
