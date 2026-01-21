from django.db import models
from model_utils.fields import MonitorField
from django.utils import timezone
from django.core.validators import MinValueValidator

from apps.core.models import BaseModel
from apps.shop.models import ProductVariant, Products
from apps.user.models import User, Address


# Create your models here.
class Cart(BaseModel):
    STATUS_ACTIVE = "active"
    STATUS_ORDERED = "ordered"
    STATUS_ABANDONED = "abandoned"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_ABANDONED, "Abandoned"),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts"
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    # store totals on save to speed up reads
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="unique_active_cart_per_user"
            ),
            models.UniqueConstraint(
                fields=["session_key"],
                condition=models.Q(status="active"),
                name="unique_active_cart_per_session"
            )
        ]

    def __str__(self):
        return f"Cart({self.user or self.session_key})"


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])  # snapshot
    line_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('cart', 'variant')

    def __str__(self):
        return f"{self.variant.sku} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.unit_price = self.unit_price or self.variant.final_price
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    
# Orders
class Order(BaseModel):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending"              # order placed, payment not confirmed yet
        PAID = "paid"                    # payment received
        FAILED = "failed"                # payment failed
        REFUNDED = "refunded"            # payment refunded
    
    class OrderStatus(models.TextChoices):
        PENDING = "pending"              # order placed, payment not confirmed yet
        CONFIRMED = "confirmed"          # payment received / COD accepted
        PROCESSING = "processing"        # warehouse preparing order
        SHIPPED = "shipped"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"
        REFUNDED = "refunded"
        COMPLETED = "completed"          # order completed
        
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    status_changed_at = MonitorField(monitor='status')
    placed_at = models.DateTimeField(default=timezone.now)
    shipped_at = models.DateTimeField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)

    def __str__(self):
        user_email = self.user.email if self.user else "guest"
        return f"Order #{self.id} - {user_email}"
    
    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["placed_at"]),
        ]
        
    def calculate_totals(self):
        items = self.items.all()
        self.subtotal = sum(i.total_price for i in items)
        self.total_amount = self.subtotal + self.shipping_fee - self.discount
        return self.total_amount


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Products, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=255)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):  
        sku = self.variant.sku if self.variant else "N/A"
        return f"OrderItem {sku} x {self.quantity}"
    
    class Meta:
        indexes = [
            models.Index(fields=["order"]),
        ]


class Payment(BaseModel):

    class PaymentStatus(models.TextChoices):
        INITIATED = "initiated"
        SUCCESS = "success"
        FAILED = "failed"
        REFUNDED = "refunded"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")

    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    method = models.CharField(max_length=50)           # bKash, COD, SSLCommerz, etc.
    transaction_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    raw_response = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return f"{self.method} - {self.amount}"


class InventoryTransaction(BaseModel):

    class TransactionType(models.TextChoices):
        PURCHASE = "purchase"          # stock added from supplier
        SALE = "sale"                  # order shipped
        RESERVE = "reserve"            # user placed order (hold)
        RELEASE = "release"            # order cancelled
        ADJUSTMENT = "adjustment"      # admin manual correction

    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="transactions")
    quantity = models.IntegerField()  # positive or negative
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)

    order = models.ForeignKey(
        "orders.Order", blank=True, null=True, on_delete=models.SET_NULL
    )

    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.product_variant.sku} - {self.transaction_type} - {self.quantity}"


class Coupon(BaseModel):
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)  # optional
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)  # optional

    def clean(self):
        from django.core.exceptions import ValidationError
        if (self.discount_amount is None) and (self.discount_percent is None):
            raise ValidationError("Coupon must have either discount_amount or discount_percent")
        if (self.discount_amount is not None) and (self.discount_percent is not None):
            raise ValidationError("Coupon cannot have both discount_amount and discount_percent")

    def is_valid(self):
        now = timezone.now()
        return self.active and (self.valid_from <= now <= self.valid_to)

    def __str__(self):
        return self.code    