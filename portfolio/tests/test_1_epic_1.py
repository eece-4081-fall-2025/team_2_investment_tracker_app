# Epic 1 unit test

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse

from portfolio.models import Portfolio, Investment, Transaction


class Epic1CoreManagementTests(TestCase):
    """
    Epic 1: Core Investment Management
    - Create/list/detail/edit/delete Portfolio
    - Create/edit/delete Investment tied to a Portfolio
    - When an Investment is created with qty & price, an initial BUY Transaction is created
    """

    def setUp(self):
        self.port = Portfolio.objects.create(name="Starter Portfolio", description="Test")

    # ---------- Portfolio CRUD ----------

    def test_portfolio_list_and_detail(self):
        # list
        resp = self.client.get(reverse("portfolio-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Starter Portfolio")

        # detail
        resp = self.client.get(reverse("portfolio-detail", args=[self.port.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.port.name)

    def test_portfolio_create_update_delete(self):
        # create
        resp = self.client.post(
            reverse("portfolio-create"),
            {"name": "New P", "description": "desc"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        new_p = Portfolio.objects.get(name="New P")

        # update
        resp = self.client.post(
            reverse("portfolio-edit", args=[new_p.pk]),
            {"name": "Renamed P", "description": "changed"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        new_p.refresh_from_db()
        self.assertEqual(new_p.name, "Renamed P")

        # delete
        resp = self.client.post(reverse("portfolio-delete", args=[new_p.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Portfolio.objects.filter(pk=new_p.pk).exists())

    # ---------- Investment CRUD + initial BUY transaction ----------

    def test_investment_create_creates_initial_buy_transaction(self):
        """
        Posting an Investment with quantity & purchase_price should:
        - create the Investment
        - auto-create a BUY Transaction(quantity, price)
        - update Investment.quantity and purchase_price via recalc
        """
        form_data = {
            "portfolio": self.port.pk,
            "name": "Apple",
            "ticker": "AAPL",
            "type": "stock",
            "quantity": "2",            # starting position
            "purchase_price": "100.00", # per-unit price
            "purchase_date": "2025-01-01",
            "notes": "",
            "current_value": "0",
            "amount_invested": "0",     # ignored by create view; kept for completeness
        }

        resp = self.client.post(reverse("investment-create"), form_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        inv = Investment.objects.get(portfolio=self.port, ticker="AAPL")
        # auto BUY created
        tx = Transaction.objects.get(investment=inv)
        self.assertEqual(tx.tx_type, Transaction.BUY)
        self.assertEqual(tx.quantity, Decimal("2"))
        self.assertEqual(tx.price, Decimal("100.00"))

        # recalc updated investment
        inv.refresh_from_db()
        self.assertEqual(inv.quantity, Decimal("2"))
        self.assertEqual(inv.purchase_price.quantize(Decimal("0.0001")), Decimal("100.0000"))

    def test_investment_update_and_delete(self):
        # seed one investment with an initial tx
        inv = Investment.objects.create(
            portfolio=self.port, name="NVIDIA", ticker="NVDA",
            quantity=0, purchase_price=0
        )
        Transaction.objects.create(
            investment=inv, tx_type=Transaction.BUY,
            quantity=Decimal("1"), price=Decimal("50.00"), fees=0, executed_at="2025-01-01"
        )
        inv.refresh_from_db()
        self.assertEqual(inv.quantity, Decimal("1"))

        # update (e.g., change name)
        resp = self.client.post(
            reverse("investment-edit", args=[inv.pk]),
            {
                "portfolio": self.port.pk,
                "name": "NVDA Corp",
                "ticker": "NVDA",
                "type": "stock",
                "quantity": inv.quantity,          # keep current qty (view ignores on update)
                "purchase_price": inv.purchase_price,
                "purchase_date": "2025-01-01",
                "notes": "",
                "current_value": "0",
                "amount_invested": "0",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        inv.refresh_from_db()
        self.assertEqual(inv.name, "NVDA Corp")

        # delete
        resp = self.client.post(reverse("investment-delete", args=[inv.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Investment.objects.filter(pk=inv.pk).exists())

    # ---------- Portfolio totals sanity (transaction-based invested) ----------

    def test_portfolio_totals_using_transactions(self):
        aapl = Investment.objects.create(portfolio=self.port, name="Apple", ticker="AAPL")
        Transaction.objects.create(
            investment=aapl, tx_type=Transaction.BUY,
            quantity=Decimal("2"), price=Decimal("100.00"), fees=0, executed_at="2025-01-01"
        )
        nvda = Investment.objects.create(portfolio=self.port, name="NVIDIA", ticker="NVDA")
        Transaction.objects.create(
            investment=nvda, tx_type=Transaction.BUY,
            quantity=Decimal("1"), price=Decimal("50.00"), fees=0, executed_at="2025-01-02"
        )

        # Invested cash is sum of BUY cash: 2*100 + 1*50 = 250
        self.assertEqual(self.port.total_invested_cash, Decimal("250.00"))
