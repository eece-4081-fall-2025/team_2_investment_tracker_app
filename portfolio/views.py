from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from .models import Portfolio, Investment
from .forms import PortfolioForm, InvestmentForm



# ---------- Portfolio views ----------
class PortfolioListView(ListView):
    model = Portfolio
    template_name = "portfolio/portfolio_list.html"


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

from .models import Portfolio, Investment
from .forms import PortfolioForm, InvestmentForm


# ---------- Portfolio views ----------
class PortfolioListView(ListView):
    model = Portfolio
    template_name = "portfolio/portfolio_list.html"


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
