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
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    coupon_code = models.CharField(max_length=32, blank=True, help_text="Snapshot of coupon code used")
    order_number = models.CharField(
        max_length=20, 
        unique=True, 
        db_index=True,
        blank=True,
        help_text="Auto-generated order number in format ORD-YYYYMMDD-XXXXX"
    )
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
        order_num = self.order_number or f"#{self.id}"
        return f"Order {order_num} - {user_email}"
    
    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["placed_at"]),
            models.Index(fields=["order_number"]),
        ]
    
    def generate_order_number(self):
        """
        Generate a unique order number in format: ORD-YYYYMMDD-XXXXX
        Example: ORD-20250115-00001
        
        The format consists of:
        - ORD: Prefix for Order
        - YYYYMMDD: Date when order was placed (8 digits)
        - XXXXX: Sequential number for the day (5 digits, zero-padded)
        
        Returns:
            str: Generated order number
        """
        from datetime import date
        
        # Get today's date
        today = date.today()
        date_str = today.strftime("%Y%m%d")
        
        # Format: ORD-YYYYMMDD-XXXXX
        prefix = f"ORD-{date_str}-"
        
        # Get all order numbers that start with today's prefix (excluding deleted)
        existing_orders = Order.objects.filter(
            order_number__startswith=prefix
        ).exclude(
            deleted=True
        ).values_list('order_number', flat=True)
        
        if existing_orders:
            # Extract sequence numbers and find the max
            max_seq = 0
            for order_num in existing_orders:
                try:
                    # Extract the sequence part (last 5 digits after the last dash)
                    seq_part = order_num.split('-')[-1]
                    seq_num = int(seq_part)
                    max_seq = max(max_seq, seq_num)
                except (ValueError, IndexError):
                    # Skip invalid order numbers
                    continue
            
            # Increment for new order
            next_seq = max_seq + 1
        else:
            # First order of the day
            next_seq = 1
        
        # Format with 5-digit zero padding
        order_number = f"{prefix}{next_seq:05d}"
        
        return order_number
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-generate order_number if not set
        """
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        super().save(*args, **kwargs)
        
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
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)  # optional
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)  # optional
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], help_text="Minimum order amount to use this coupon")
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], help_text="Maximum discount amount (for percentage coupons)")

    class Meta:
        indexes = [
            models.Index(fields=['code', 'active']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if (self.discount_amount is None) and (self.discount_percent is None):
            raise ValidationError("Coupon must have either discount_amount or discount_percent")
        if (self.discount_amount is not None) and (self.discount_percent is not None):
            raise ValidationError("Coupon cannot have both discount_amount and discount_percent")
        if self.discount_percent and self.discount_percent > 100:
            raise ValidationError("Discount percent cannot exceed 100%")

    def is_valid(self):
        """Check if coupon is active and within valid date range"""
        if not self.active:
            return False
        
        if not self.valid_from or not self.valid_to:
            return False
        
        now = timezone.now()
        return self.valid_from <= now <= self.valid_to
    
    def get_usage_count(self):
        """Get total usage count"""
        return self.usage_history.filter(order__deleted=False).count()
    
    def get_user_usage_count(self, user):
        """Get usage count for specific user"""
        if not user:
            return 0
        return self.usage_history.filter(user=user, order__deleted=False).count()
    
    def can_be_used_by_user(self, user, subtotal=0):
        """Check if coupon can be used by user"""
        # Check validity
        if not self.is_valid():
            return False, "Coupon is not valid or expired"
        
        # Check minimum order amount
        if self.min_order_amount and subtotal < self.min_order_amount:
            return False, f"Minimum order amount is {self.min_order_amount}"
        
        # Check max uses
        if self.max_uses:
            total_uses = self.get_usage_count()
            if total_uses >= self.max_uses:
                return False, "Coupon usage limit reached"
        
        # Check per-user limit
        if self.per_user_limit and user:
            user_uses = self.get_user_usage_count(user)
            if user_uses >= self.per_user_limit:
                return False, "You have reached the usage limit for this coupon"
        
        return True, "Coupon is valid"
    
    def calculate_discount(self, subtotal):
        """Calculate discount amount based on subtotal"""
        if self.discount_amount:
            discount = self.discount_amount
        elif self.discount_percent:
            discount = (subtotal * self.discount_percent) / 100
            # Apply max discount cap if set
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = 0
        
        # Discount cannot exceed subtotal
        return min(discount, subtotal)

    def __str__(self):
        return self.code


class CouponUsage(BaseModel):
    """Track coupon usage history"""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usage_history')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='coupon_usage')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    class Meta:
        indexes = [
            models.Index(fields=['coupon', 'user']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else "guest"
        return f"{self.coupon.code} used by {user_email} on Order #{self.order.id}"    