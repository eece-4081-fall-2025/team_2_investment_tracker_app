from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings




# =======================
# Portfolio Model
# =======================
class Portfolio(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
        null=True, blank=True,
    )
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
    def total_invested_cash(self):
        """Sum of all BUY cash (qty*price + fees) across this portfolio."""
        total = Decimal("0")
        for inv in self.investments.all():
            total += inv.invested_cash
        return total

    @property
    def total_net_invested_cash(self):
        """Optional: buys minus sell proceeds across this portfolio."""
        total = Decimal("0")
        for inv in self.investments.all():
            total += inv.net_invested_cash
        return total

    @property
    def total_gain_loss(self):
        return self.total_current_value - self.total_invested

    def get_absolute_url(self):
        return reverse("portfolio-detail", args=[self.pk])


# =======================
# Investment Model
# =======================
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

    # This field stays as an initial record of the first purchase
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
        # Normalize ticker, but don't auto-overwrite amount_invested
        if self.ticker:
            self.ticker = self.ticker.upper()
        super().save(*args, **kwargs)

    def gain_loss(self):
        return self.current_value - self.amount_invested

    def get_absolute_url(self):
        return reverse("portfolio-detail", args=[self.portfolio_id])

    def recalc_from_transactions(self):
        """
        Recompute quantity and cost basis (avg cost) based on transactions.
        Does NOT overwrite the manually-entered initial investment.
        """
        qty = Decimal("0")
        avg_cost = Decimal("0")

        for tx in self.transactions.all().order_by("executed_at", "id"):
            if tx.tx_type == Transaction.BUY:
                total_cost_before = avg_cost * qty
                total_cost_after = total_cost_before + (tx.quantity * tx.price) + tx.fees
                qty += tx.quantity
                avg_cost = (total_cost_after / qty).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            else:  # SELL
                if tx.quantity > qty:
                    raise ValidationError("Sell quantity exceeds current position.")
                qty -= tx.quantity

        self.quantity = qty
        self.purchase_price = avg_cost
        self.save(update_fields=["quantity", "purchase_price"])

    # ---------- Computed properties ----------
    @property
    def invested_cash(self) -> Decimal:
        """Cumulative cash in: sum of BUY (qty*price + fees)."""
        total = Decimal("0")
        for tx in self.transactions.all():
            if tx.tx_type == Transaction.BUY:
                total += (tx.quantity * tx.price) + (tx.fees or 0)
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def proceeds_cash(self) -> Decimal:
        """Cash received from SELL (qty*price - fees)."""
        total = Decimal("0")
        for tx in self.transactions.all():
            if tx.tx_type == Transaction.SELL:
                total += (tx.quantity * tx.price) - (tx.fees or 0)
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def net_invested_cash(self) -> Decimal:
        """Optional: buys minus sell proceeds."""
        return (self.invested_cash - self.proceeds_cash).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =======================
# Transaction Model
# =======================
class Transaction(models.Model):
    BUY = "BUY"
    SELL = "SELL"
    TX_TYPES = [(BUY, "Buy"), (SELL, "Sell")]

    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name="transactions")
    tx_type = models.CharField(max_length=4, choices=TX_TYPES)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    price = models.DecimalField(max_digits=18, decimal_places=4)
    fees = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.00"))
    executed_at = models.DateField()

    @property
    def total_cost(self):
        """Total cash out/in for this transaction."""
        return self.quantity * self.price + self.fees

    class Meta:
        ordering = ["executed_at", "id"]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if self.price < 0:
            raise ValidationError("Price cannot be negative.")

    def __str__(self):
        return f"{self.tx_type} {self.quantity} @ {self.price} ({self.investment.ticker})"


# =======================
# Signals
# =======================
@receiver([post_save, post_delete], sender=Transaction)
def _recalc_investment_on_tx_change(sender, instance, **kwargs):
    """Recalculate the investment after any transaction change."""
    instance.investment.recalc_from_transactions()
