from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import BaseModel
# Create your models here.

class Categories(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class Products(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=140, unique=True)
    category = models.ForeignKey(Categories, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    # tags = models.ManyToManyField("Tag", blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_featured']),
        ]
        ordering = ['-created']

    def __str__(self):
        return self.name
    
    
class ProductImages(BaseModel):
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    alt_text = models.CharField(max_length=255, blank=True)
    ordering = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['ordering', 'id']

    def __str__(self):
        return self.product.name
    
    

class ProductVariant(BaseModel):
    """
    e.g., 250g roasted almond, 500g flavored almonds
    """
    class DiscountTypeChoices(models.TextChoices):
        AMOUNT = 'amount', 'Amount'
        PERCENT = 'percent', 'Percent'
    
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    sku = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=200, blank=True)  # "250g - Roasted"
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )  # selling price
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True, blank=True
    )
    weight_grams = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True, blank=True
    )
    barcode = models.CharField(max_length=128, blank=True, null=True)
    on_sale = models.BooleanField(default=False)
    discount_type = models.CharField(
        max_length=10, 
        choices=DiscountTypeChoices.choices,
        default=DiscountTypeChoices.AMOUNT,
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True, blank=True
    )
    # tags = models.ManyToManyField("Tag", blank=True)
    available_from = models.DateTimeField(null=True, blank=True)
    available_to = models.DateTimeField(null=True, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


    class Meta:
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['product', 'is_active']),
        ]
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.product.name} - {self.name or self.sku}"
    
    @property
    def final_price(self):
        if not self.on_sale or not self.discount_value:
            return self.price
        if self.discount_type == self.DiscountTypeChoices.AMOUNT:
            return max(self.price - self.discount_value, 0)
        return max(self.price * (1 - self.discount_value / 100), 0)
        
class ProductVariantImage(BaseModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='product_variant_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['ordering', 'id']
        
    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.name or self.variant.sku}"
    
    
class Inventory(models.Model):
    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)    # actual stock
    low_stock_threshold = models.PositiveIntegerField(default=5)

    class Meta:
        indexes = [
            models.Index(fields=['quantity']),
        ]

    def __str__(self):
        return f"{self.variant.sku} - {self.quantity}"

    @property
    def reserved(self):
        from apps.orders.models import InventoryTransaction
        # sum of outstanding reserved transactions
        result = self.variant.transactions.filter(
            transaction_type=InventoryTransaction.TransactionType.RESERVE
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        # Note: RESERVE transactions should be negative qty (see services)
        return abs(result)

    @property
    def available(self):
        return max(self.quantity - self.reserved, 0)


class ProductRating(BaseModel):
    """
    Product rating and review model.
    Allows users to rate products (1-5 stars) and optionally leave a review.
    """
    product = models.ForeignKey(
        Products, 
        on_delete=models.CASCADE, 
        related_name='ratings'
    )
    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='product_ratings',
        null=True,
        blank=True
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    review = models.TextField(
        blank=True,
        null=True,
        help_text="Optional review text"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rating is active/approved"
    )
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="Whether the user has purchased this product"
    )

    class Meta:
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['rating']),
        ]
        ordering = ['-created']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'user'],
                condition=models.Q(deleted=False),
                name='unique_rating_per_user_per_product'
            )
        ]

    def __str__(self):
        user_name = self.user.email if self.user else "Anonymous"
        return f"{self.product.name} - {self.rating} stars by {user_name}"
    
    @property
    def average_rating_for_product(self):
        """
        Calculate average rating for the product.
        This can be used as a method or property on the Product model.
        """
        return ProductRating.objects.filter(
            product=self.product,
            is_active=True,
            deleted=False
        ).aggregate(avg_rating=models.Avg('rating'))['avg_rating'] or 0