from django.contrib import admin
from .models import Portfolio, Investment


class InvestmentInline(admin.TabularInline):
    model = Investment
    extra = 0


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    inlines = [InvestmentInline]


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ("name", "ticker", "type", "portfolio", "amount_invested", "current_value")
