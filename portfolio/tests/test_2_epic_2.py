from decimal import Decimal
from django.test import TestCase
from django.urls import reverse

from portfolio.models import Portfolio, Investment, Transaction


class Epic2PortfolioOverviewTests(TestCase):
    """
    Epic 2: Portfolio Overview (main menu)
    - Portfolio invested cash is based on transactions (invested_cash)
    - Portfolio list page renders the overview and JS hook attributes
      needed for live net worth (data-ticker, data-qty, data-invested)
    """

    def setUp(self):
        # One portfolio with two positions
        self.port = Portfolio.objects.create(name="Overview P")

        self.aapl = Investment.objects.create(
            portfolio=self.port,
            name="Apple",
            ticker="AAPL",
        )
        self.nvda = Investment.objects.create(
            portfolio=self.port,
            name="NVIDIA",
            ticker="NVDA",
        )

        # AAPL: BUY 2 @ 100
        Transaction.objects.create(
            investment=self.aapl,
            tx_type=Transaction.BUY,
            quantity=Decimal("2"),
            price=Decimal("100.00"),
            fees=Decimal("0.00"),
            executed_at="2025-01-01",
        )
        # NVDA: BUY 1 @ 50
        Transaction.objects.create(
            investment=self.nvda,
            tx_type=Transaction.BUY,
            quantity=Decimal("1"),
            price=Decimal("50.00"),
            fees=Decimal("0.00"),
            executed_at="2025-01-02",
        )

        # Refresh from DB so recalc_from_transactions has run
        self.aapl.refresh_from_db()
        self.nvda.refresh_from_db()
        self.port.refresh_from_db()

    def test_invested_cash_per_investment(self):
        """
        Each Investment should track invested_cash from its BUY transactions:
        AAPL: 2 * 100 = 200
        NVDA: 1 * 50  = 50
        """
        self.assertEqual(self.aapl.invested_cash, Decimal("200.00"))
        self.assertEqual(self.nvda.invested_cash, Decimal("50.00"))

    def test_portfolio_total_invested_cash(self):
        """
        Portfolio.total_invested_cash should be the sum of child invested_cash.
        """
        self.assertEqual(self.port.total_invested_cash, Decimal("250.00"))

    def test_portfolio_list_overview_renders_invested_and_js_hooks(self):
        """
        The main menu (portfolio list) must:
        - show the human-readable invested total
        - include hidden .positions/.pos spans with data-ticker, data-qty, data-invested
          for the JS live net worth updater.
        """
        url = reverse("portfolio-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        html = resp.content.decode()

        # Heading for this epic's feature
        self.assertIn("Total Net Worth (live)", html)
        # Portfolio name appears
        self.assertIn("Overview P", html)
        # Invested total should be rendered as $250.00
        self.assertIn("Invested: $250.00", html.replace("&nbsp;", " "))

        # JS hooks: positions container and per-position spans
        self.assertIn('class="positions"', html)
        # AAPL position with correct attributes
        self.assertIn('data-ticker="AAPL"', html)
        self.assertIn('data-qty="2', html)          # 2 shares
        self.assertIn('data-invested="200.00"', html)
        # NVDA position with correct attributes
        self.assertIn('data-ticker="NVDA"', html)
        self.assertIn('data-qty="1', html)
        self.assertIn('data-invested="50.00"', html)
