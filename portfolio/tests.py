from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from .models import Portfolio, Investment  # <-- this line is crucial



class AddInvestmentTests(TestCase):
    def setUp(self):
        self.p = Portfolio.objects.create(name="Retirement")

    def test_create_investment_and_compute_amount(self):
        """
        POST to investment-create with valid data:
        - creates an Investment
        - uppercases ticker
        - computes amount_invested = quantity * purchase_price
        - redirects (302)
        """
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
        self.assertEqual(inv.quantity, Decimal("10"))
        self.assertEqual(inv.purchase_price, Decimal("150.00"))
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

        # stays on same page
        self.assertEqual(resp.status_code, 200)

        form = resp.context["form"]
        self.assertIn("Quantity must be > 0", form.errors["quantity"])
        self.assertIn("Purchase price must be > 0", form.errors["purchase_price"])


class EditInvestmentTests(TestCase):
    def setUp(self):
        self.p = Portfolio.objects.create(name="Core")
        self.inv = Investment.objects.create(
            portfolio=self.p,
            name="Apple",
            ticker="AAPL",
            type="stock",
            quantity=Decimal("10"),
            purchase_price=Decimal("100.00"),
            purchase_date="2025-10-01",
            current_value=Decimal("1100.00"),
            notes="initial",
        )

    def test_edit_updates_fields_and_recomputes_amount_invested(self):
        """
        Editing an investment should:
        - update fields
        - re-normalize ticker to uppercase
        - recompute amount_invested
        - redirect after success
        """
        url = reverse("investment-edit", args=[self.inv.pk])

        resp = self.client.post(url, {
            "portfolio": self.p.id,
            "name": "Apple Inc.",
            "ticker": "aapl",
            "type": "stock",
            "quantity": "12",
            "purchase_price": "120.00",
            "purchase_date": "2025-10-02",
            "current_value": "1500.00",
            "notes": "updated",
        })

        self.assertEqual(resp.status_code, 302)

        self.inv.refresh_from_db()
        self.assertEqual(self.inv.name, "Apple Inc.")
        self.assertEqual(self.inv.ticker, "AAPL")
        self.assertEqual(self.inv.quantity, Decimal("12"))
        self.assertEqual(self.inv.purchase_price, Decimal("120.00"))
        self.assertEqual(self.inv.amount_invested, Decimal("1440.00"))
        self.assertEqual(self.inv.current_value, Decimal("1500.00"))
        self.assertEqual(self.inv.notes, "updated")
        self.assertEqual(self.inv.portfolio, self.p)


class DeleteInvestmentTests(TestCase):
    def setUp(self):
        self.p = Portfolio.objects.create(name="Delete Test")
        self.inv = Investment.objects.create(
            portfolio=self.p,
            name="Temporary",
            ticker="TMP",
            type="stock",
            quantity=Decimal("1"),
            purchase_price=Decimal("100.00"),
            purchase_date="2025-10-01",
            current_value=Decimal("100.00"),
        )

    def test_delete_investment_removes_it_and_redirects(self):
        """
        Deleting an investment should:
        - show a confirm page on GET
        - delete on POST
        - redirect back to portfolio detail
        """
        url = reverse("investment-delete", args=[self.inv.pk])

        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 200)

        post_resp = self.client.post(url)
        self.assertEqual(post_resp.status_code, 302)

        exists = Investment.objects.filter(pk=self.inv.pk).exists()
        self.assertFalse(exists)
