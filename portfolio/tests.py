from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from .models import Portfolio, Investment


class AddInvestmentTests(TestCase):
    def setUp(self):
        self.p = Portfolio.objects.create(name="Retirement")

    def test_create_investment_and_compute_amount(self):
        # ... keep your existing first test as-is ...
        url = reverse("investment-create")
        resp = self.client.post(url, {
            "portfolio": self.p.id,
            "name": "Apple Inc.",
            "ticker": "aapl",
            "type": "stock",
            "quantity": "10",
            "purchase_price": "150.00",
            "purchase_date": "2025-10-01",
            "current_value": "1600.00",
            "notes": "test buy",
        })
        self.assertEqual(resp.status_code, 302)
        inv = Investment.objects.get(ticker="AAPL")
        self.assertEqual(inv.amount_invested, Decimal("1500.00"))
        self.assertEqual(inv.portfolio, self.p)

    def test_validation_positive_quantity_and_price(self):
        """
        Quantity and purchase_price must both be > 0.
        """
        url = reverse("investment-create")
        resp = self.client.post(url, {
            "portfolio": self.p.id,
            "name": "Bad",
            "ticker": "BAD",
            "type": "stock",
            "quantity": "-5",
            "purchase_price": "0",
            "purchase_date": "2025-10-01",
            "current_value": "0",
        })

        # stays on the same page
        self.assertEqual(resp.status_code, 200)

        # get the bound form from the context
        form = resp.context["form"]

        # field-level errors should contain our custom messages
        self.assertIn("Quantity must be > 0", form.errors["quantity"])
        self.assertIn("Purchase price must be > 0", form.errors["purchase_price"])
