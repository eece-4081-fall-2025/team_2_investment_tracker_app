from django.db import models
from django.urls import reverse
from decimal import Decimal


class Portfolio(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def total_invested(self):
        from django.db.models import Sum
        agg = self.investments.aggregate(total=Sum("amount_invested"))
        return agg["total"] or Decimal("0")

    @property
    def total_current_value(self):
        from django.db.models import Sum
        agg = self.investments.aggregate(total=Sum("current_value"))
        return agg["total"] or Decimal("0")

    @property
    def total_gain_loss(self):
        return self.total_current_value - self.total_invested

    def get_absolute_url(self):
        return reverse("portfolio-detail", args=[self.pk])


class Investment(models.Model):
    TYPE_CHOICES = [
        ("stock", "Stock"),
        ("bond", "Bond"),
        ("crypto", "Crypto"),
        ("fund", "Index/Mutual Fund"),
        ("annuity", "Annuity"),
        ("other", "Other"),
    ]

    portfolio = models.ForeignKey(
        Portfolio,
        related_name="investments",
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=200)
    ticker = models.CharField(max_length=12, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="stock")

    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    purchase_date = models.DateField(null=True, blank=True)

    amount_invested = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    current_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        label = self.ticker or self.name
        return f"{label} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        # normalize ticker, compute amount_invested before saving
        if self.ticker:
            self.ticker = self.ticker.upper()
        self.amount_invested = (self.quantity or 0) * (self.purchase_price or 0)
        super().save(*args, **kwargs)

    def gain_loss(self):
        return self.current_value - self.amount_invested

    def get_absolute_url(self):
        return reverse("portfolio-detail", args=[self.portfolio_id])
