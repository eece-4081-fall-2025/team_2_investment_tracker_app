from datetime import date
from decimal import Decimal

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .models import Portfolio, Investment, Transaction
from .forms import PortfolioForm, InvestmentForm, TransactionForm


# ---------- Portfolio views ----------
class PortfolioListView(ListView):
    model = Portfolio
    template_name = "portfolio/portfolio_list.html"

    # Prefetch investments so templates can loop p.investments without extra queries
    def get_queryset(self):
        return super().get_queryset().prefetch_related("investments")


class PortfolioDetailView(DetailView):
    model = Portfolio
    template_name = "portfolio/portfolio_detail.html"


class PortfolioCreateView(CreateView):
    model = Portfolio
    form_class = PortfolioForm
    template_name = "portfolio/portfolio_form.html"


class PortfolioUpdateView(UpdateView):
    model = Portfolio
    form_class = PortfolioForm
    template_name = "portfolio/portfolio_form.html"


class PortfolioDeleteView(DeleteView):
    model = Portfolio
    success_url = reverse_lazy("portfolio-list")
    template_name = "portfolio/confirm_delete.html"


# ---------- Investment views ----------
class InvestmentCreateView(CreateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "portfolio/investment_form.html"

    # Pre-fill portfolio when coming from ?portfolio=<id>
    def get_initial(self):
        initial = super().get_initial()
        pid = self.request.GET.get("portfolio")
        if pid:
            initial["portfolio"] = pid
        return initial

    def form_valid(self, form):
        # Attach portfolio if provided via query or POST
        pid = self.request.GET.get("portfolio") or self.request.POST.get("portfolio")
        if pid:
            form.instance.portfolio_id = pid

        response = super().form_valid(form)
        inv = self.object

        # If the user entered a starting position, record it as the first BUY transaction
        if (inv.quantity or 0) > 0 and (inv.purchase_price or 0) > 0 and not inv.transactions.exists():
            Transaction.objects.create(
                investment=inv,
                tx_type=Transaction.BUY,
                quantity=inv.quantity,          # per-unit math
                price=inv.purchase_price,       # per-unit price
                fees=Decimal("0.00"),
                executed_at=inv.purchase_date or date.today(),
            )
            # Investment gets recalculated by the Transaction signal in models.py
        return response


class InvestmentUpdateView(UpdateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "portfolio/investment_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        inv = self.object
        # If an existing investment is updated to include a starting position and still has no transactions, backfill one
        if (inv.quantity or 0) > 0 and (inv.purchase_price or 0) > 0 and not inv.transactions.exists():
            Transaction.objects.create(
                investment=inv,
                tx_type=Transaction.BUY,
                quantity=inv.quantity,
                price=inv.purchase_price,
                fees=Decimal("0.00"),
                executed_at=inv.purchase_date or date.today(),
            )
        return response


class InvestmentDeleteView(DeleteView):
    model = Investment
    template_name = "portfolio/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("portfolio-detail", args=[self.object.portfolio_id])


# ---------- API ----------
def ticker_info(request):
    """
    Return JSON with a live price for the given ticker.
    Tries yfinance first; falls back to most recent stored value from Investment.
    Structure: {"ticker": "AAPL", "price": "268.47" or null}
    """
    ticker = (request.GET.get("ticker") or "").strip().upper()
    data = {"ticker": ticker, "price": None}
    if not ticker:
        return JsonResponse(data)

    # 1) Try yfinance live/last close
    try:
        import yfinance as yf
        yf_ticker = yf.Ticker(ticker)
        info = getattr(yf_ticker, "fast_info", None)
        price = None
        if info is not None:
            try:
                price = (
                    getattr(info, "last_price", None)
                    or getattr(info, "last_close", None)
                    or getattr(info, "previous_close", None)
                )
            except Exception:
                price = None
            if price is None and isinstance(info, dict):
                price = info.get("last_price") or info.get("last_close") or info.get("previous_close")
        if price is None:
            hist = yf_ticker.history(period="1d")
            if hasattr(hist, "empty") and not hist.empty and "Close" in hist:
                price = float(hist["Close"].iloc[-1])
        if price is not None:
            data["price"] = f"{price:.2f}"
            return JsonResponse(data)
    except Exception:
        # ignore and try DB fallback
        pass

    # 2) Fallback to our DB: last purchase_price or current_value/quantity
    try:
        qs = Investment.objects.filter(ticker=ticker).order_by("-purchase_date", "-created_at")
        obj = qs.first()
        if obj and getattr(obj, "purchase_price", None) is not None:
            data["price"] = str(obj.purchase_price)
        elif obj and getattr(obj, "current_value", None) is not None and getattr(obj, "quantity", None):
            qty = obj.quantity or 0
            if qty:
                data["price"] = str(obj.current_value / qty)
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
