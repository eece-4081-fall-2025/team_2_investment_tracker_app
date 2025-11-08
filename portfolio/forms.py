from django import forms
from decimal import Decimal

from .models import Portfolio, Investment


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ["name", "description"]


class InvestmentForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = [
            "portfolio",
            "name",
            "ticker",
            "type",
            "quantity",
            "purchase_price",
            "purchase_date",
            "current_value",
            "notes",
        ]

    def clean(self):
        cleaned = super().clean()
        qty = cleaned.get("quantity") or Decimal("0")
        price = cleaned.get("purchase_price") or Decimal("0")

        if qty <= 0:
            self.add_error("quantity", "Quantity must be > 0")
        if price <= 0:
            self.add_error("purchase_price", "Purchase price must be > 0")

        return cleaned
