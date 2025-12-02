from datetime import date
from decimal import Decimal

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

from .models import Portfolio, Investment, Transaction
from .forms import PortfolioForm, InvestmentForm, TransactionForm


# ---------- Portfolio views ----------
class PortfolioListView(LoginRequiredMixin, ListView):
    model = Portfolio
    template_name = "portfolio/portfolio_list.html"

    def get_queryset(self):
        return (
            Portfolio.objects.filter(user=self.request.user)
            .prefetch_related("investments")
        )


class PortfolioDetailView(LoginRequiredMixin, DetailView):
    model = Portfolio
    template_name = "portfolio/portfolio_detail.html"

    def get_queryset(self):
        return (
            Portfolio.objects.filter(user=self.request.user)
            .prefetch_related("investments")
        )


class PortfolioCreateView(LoginRequiredMixin, CreateView):
    model = Portfolio
    form_class = PortfolioForm
    template_name = "portfolio/portfolio_form.html"
    success_url = reverse_lazy("portfolio-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class PortfolioUpdateView(LoginRequiredMixin, UpdateView):
    model = Portfolio
    form_class = PortfolioForm
    template_name = "portfolio/portfolio_form.html"
    success_url = reverse_lazy("portfolio-list")

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)


class PortfolioDeleteView(LoginRequiredMixin, DeleteView):
    model = Portfolio
    template_name = "portfolio/confirm_delete.html"
    success_url = reverse_lazy("portfolio-list")

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)


# ---------- Investment views ----------
class InvestmentCreateView(LoginRequiredMixin, CreateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "portfolio/investment_form.html"

    def get_initial(self):
        initial = super().get_initial()
        pid = self.request.GET.get("portfolio")
        if pid:
            try:
                initial["portfolio"] = Portfolio.objects.get(
                    pk=pid, user=self.request.user
                )
            except Portfolio.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        # Force portfolio to belong to this user (defensive)
        portfolio = form.cleaned_data.get("portfolio")
        if portfolio.user != self.request.user:
            form.add_error("portfolio", "Invalid portfolio.")
            return self.form_invalid(form)

        response = super().form_valid(form)
        inv = self.object

        # If the user specified an initial quantity/price and there are no
        # transactions yet, create an initial BUY transaction automatically.
        if (
            (inv.quantity or 0) > 0
            and (inv.purchase_price or 0) > 0
            and not inv.transactions.exists()
        ):
            Transaction.objects.create(
                investment=inv,
                tx_type=Transaction.BUY,
                quantity=inv.quantity,
                price=inv.purchase_price,
                fees=Decimal("0.00"),
                executed_at=inv.purchase_date or date.today(),
            )

        return response


class InvestmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "portfolio/investment_form.html"

    def get_queryset(self):
        return Investment.objects.filter(portfolio__user=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        inv = self.object

        # Same idea as in create: if we *still* have no txs but now have a
        # quantity + price, backfill a starting BUY transaction.
        if (
            (inv.quantity or 0) > 0
            and (inv.purchase_price or 0) > 0
            and not inv.transactions.exists()
        ):
            Transaction.objects.create(
                investment=inv,
                tx_type=Transaction.BUY,
                quantity=inv.quantity,
                price=inv.purchase_price,
                fees=Decimal("0.00"),
                executed_at=inv.purchase_date or date.today(),
            )

        return response


class InvestmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Investment
    template_name = "portfolio/confirm_delete.html"

    def get_queryset(self):
        return Investment.objects.filter(portfolio__user=self.request.user)

    def get_success_url(self):
        return reverse("portfolio-detail", args=[self.object.portfolio_id])


# ---------- API views ----------
def ticker_info(request):
    """
    Return JSON info about a ticker, including a 'price' field if one can be determined.
    """
    ticker = (request.GET.get("ticker") or "").strip().upper()
    data = {"ticker": ticker, "price": None}
    if not ticker:
        return JsonResponse(data)

    # 1) Try live data via yfinance
    try:
        import yfinance as yf

        yf_t = yf.Ticker(ticker)
        fast = getattr(yf_t, "fast_info", None)
        price = None

        if fast:
            try:
                price = (
                    getattr(fast, "last_price", None)
                    or getattr(fast, "last_close", None)
                    or getattr(fast, "previous_close", None)
                )
            except Exception:
                price = None
            if price is None and isinstance(fast, dict):
                price = (
                    fast.get("last_price")
                    or fast.get("last_close")
                    or fast.get("previous_close")
                )

        if price is None:
            hist = yf_t.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        if price is not None:
            data["price"] = f"{price:.2f}"
            return JsonResponse(data)
    except Exception:
        pass

    # 2) Fallback to our DB
    try:
        obj = (
            Investment.objects.filter(ticker=ticker)
            .order_by("-purchase_date", "-created_at")
            .first()
        )
        if obj and obj.purchase_price:
            data["price"] = str(obj.purchase_price)
        elif obj and obj.current_value and obj.quantity:
            data["price"] = f"{(obj.current_value / obj.quantity):.2f}"
    except Exception:
        pass

    return JsonResponse(data)


def list_tickers(request):
    """Return a JSON array of distinct tickers already in the system."""
    try:
        tickers = (
            Investment.objects.exclude(ticker__isnull=True)
            .exclude(ticker__exact="")
            .values_list("ticker", flat=True)
            .distinct()
        )
        tickers = sorted({t.upper() for t in tickers})
    except Exception:
        tickers = []
    return JsonResponse({"tickers": tickers})


@login_required
def portfolio_history(request, pk):
    """
    Return historical *average price* for this portfolio.

    Query param 'range' controls window:
      - 7d  -> last 7 days
      - 1mo -> last month
      - 1y  -> last year
      - 5y  -> last 5 years
    """
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)

    range_key = (request.GET.get("range") or "7d").lower()
    # Map range key to yfinance period + interval
    if range_key == "1mo":
        period, interval = "1mo", "1d"
    elif range_key == "1y":
        period, interval = "1y", "1wk"
    elif range_key == "5y":
        period, interval = "5y", "1mo"
    else:  # default 7d
        range_key = "7d"
        period, interval = "7d", "1d"

    # Aggregate holdings: {TICKER: total_qty}
    holdings = {}
    for inv in portfolio.investments.all():
        if inv.ticker and inv.quantity and inv.quantity > 0:
            t = inv.ticker.upper()
            holdings[t] = holdings.get(t, 0.0) + float(inv.quantity)

    if not holdings:
        return JsonResponse({"points": [], "range": range_key})

    try:
        import yfinance as yf
    except Exception:
        return JsonResponse({"points": [], "range": range_key})

    from collections import defaultdict

    daily = defaultdict(lambda: {"val": 0.0, "qty": 0.0})

    for ticker, qty in holdings.items():
        try:
            hist = yf.Ticker(ticker).history(period=period, interval=interval)
            if hist.empty or "Close" not in hist:
                continue
            for ts, price in hist["Close"].items():
                d = ts.date().isoformat()
                price_f = float(price)
                daily[d]["val"] += price_f * qty
                daily[d]["qty"] += qty
        except Exception:
            continue

    points = []
    for d in sorted(daily.keys()):
        if daily[d]["qty"] > 0:
            avg_price = daily[d]["val"] / daily[d]["qty"]
            points.append({"date": d, "value": round(avg_price, 2)})

    return JsonResponse({"points": points, "range": range_key})


# ---------- Transaction views ----------
class TransactionCreateView(CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "portfolio/transaction_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.investment = get_object_or_404(Investment, pk=kwargs["investment_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.investment = self.investment
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("portfolio-detail", args=[self.investment.portfolio_id])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["investment"] = self.investment
        return ctx


# ---------- Auth views ----------
class SignUpView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")
