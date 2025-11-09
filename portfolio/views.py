from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Max

from .models import Portfolio, Investment
from .forms import PortfolioForm, InvestmentForm



# ---------- Portfolio views ----------
class PortfolioListView(ListView):
    model = Portfolio
    template_name = "portfolio/portfolio_list.html"

    def get_queryset(self): 
        return super().get_queryset().prefetch_related('investments')  # makes p.investments.all more efficient by prefetching investments


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


class InvestmentUpdateView(UpdateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "portfolio/investment_form.html"


class InvestmentDeleteView(DeleteView):
    model = Investment
    template_name = "portfolio/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("portfolio-detail", args=[self.object.portfolio_id])
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Max

from .models import Portfolio, Investment
from .forms import PortfolioForm, InvestmentForm


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
            # fast_info may be object- or dict-like depending on version
            try:
                price = getattr(info, "last_price", None) or getattr(info, "last_close", None) or getattr(info, "previous_close", None)
            except Exception:
                price = None
            if price is None and isinstance(info, dict):
                price = info.get("last_price") or info.get("last_close") or info.get("previous_close")
        if price is None:
            # Fallback to history (last known close)
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
        # Using values_list distinct to gather unique, non-empty tickers
        tickers = list(Investment.objects.exclude(ticker__isnull=True).exclude(ticker__exact="").values_list("ticker", flat=True).distinct())
        tickers = sorted({t.upper() for t in tickers})
    except Exception:
        tickers = []
    return JsonResponse({"tickers": tickers})
