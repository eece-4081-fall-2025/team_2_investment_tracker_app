from django import forms
from decimal import Decimal

from .models import Portfolio, Investment, Transaction


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ["name", "description"]


class InvestmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make ticker field suggest existing tickers via datalist while still allowing free text
        if 'ticker' in self.fields:
            self.fields['ticker'].widget.attrs.setdefault('list', 'ticker-options')
            self.fields['ticker'].widget.attrs.setdefault('placeholder', 'Start typing to pick a ticker…')
        # Optionally, set an ID on purchase_price for JS to target
        if 'purchase_price' in self.fields:
            self.fields['purchase_price'].widget.attrs.setdefault('id', 'id_purchase_price')

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
            "notes",
        ]

        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}), # calendar widget
        }

    def clean(self):
        cleaned = super().clean()
        qty = cleaned.get("quantity") or Decimal("0")
        price = cleaned.get("purchase_price") or Decimal("0")

        if qty <= 0:
            self.add_error("quantity", "Quantity must be > 0")
        if price <= 0:
            self.add_error("purchase_price", "Purchase price must be > 0")

        return cleaned

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["tx_type", "quantity", "price", "fees", "executed_at"]
        widgets = {
            "tx_type": forms.Select(),
            "quantity": forms.NumberInput(attrs={"step": "1"}),
            "price": forms.NumberInput(attrs={"step": "0.01"}),
            "fees": forms.NumberInput(attrs={"step": "0.01"}),
            "executed_at": forms.DateInput(attrs={"type": "date"}),
        }
