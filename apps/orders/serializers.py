from rest_framework import serializers
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import (
    Cart, CartItem, Order, OrderItem, Payment, Coupon, InventoryTransaction
)
from apps.shop.models import ProductVariant, Inventory
from apps.user.models import Address


# Cart Serializers
class CartItemSerializer(serializers.ModelSerializer):
    variant_detail = serializers.SerializerMethodField()
    variant_id = serializers.IntegerField(write_only=True)
    product_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'variant_id', 'variant_detail', 'product_detail', 'quantity', 'unit_price', 'line_total', 'created', 'last_modified']
        read_only_fields = ['id', 'unit_price', 'line_total', 'created', 'last_modified']
    
    def get_variant_detail(self, obj):
        from apps.shop.serializers import ProductVariantSerializer
        request = self.context.get('request')
        return ProductVariantSerializer(obj.variant, context={'request': request}).data
    
    def get_product_detail(self, obj):
        if obj.variant and obj.variant.product:
            from apps.shop.serializers import ProductSerializer
            request = self.context.get('request')
            return ProductSerializer(obj.variant.product, context={'request': request}).data
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'session_key', 'status', 'subtotal', 'item_count', 'items', 'created', 'last_modified']
        read_only_fields = ['id', 'user', 'session_key', 'status', 'subtotal', 'created', 'last_modified']
    
    def get_item_count(self, obj):
        return obj.items.count()
    
    def to_representation(self, instance):
        # Ensure request context is passed to nested serializers
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            # Re-serialize items with request context
            representation['items'] = [
                CartItemSerializer(item, context={'request': request}).data
                for item in instance.items.all()
            ]
        return representation


class AddToCartSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    
    # def validate_variant_id(self, value):
    #     try:
    #         variant = ProductVariant.objects.get(id=value, is_active=True)
    #         # Check inventory
    #         try:
    #             inv = Inventory.objects.get(variant=variant)
    #             if inv.available < self.initial_data.get('quantity', 1):
    #                 raise serializers.ValidationError(f"Insufficient stock. Available: {inv.available}")
    #         except Inventory.DoesNotExist:
    #             pass  # No inventory tracking for this variant
    #         return value
    #     except ProductVariant.DoesNotExist:
    #         raise serializers.ValidationError("Product variant not found or inactive")


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_quantity(self, value):
        # cart_item = self.context.get('cart_item')
        # if cart_item:
        #     try:
        #         inv = Inventory.objects.get(variant=cart_item.variant)
        #         if inv.available < value:
        #             raise serializers.ValidationError(f"Insufficient stock. Available: {inv.available}")
        #     except Inventory.DoesNotExist:
        #         pass
        return value


# Order Serializers
class OrderItemSerializer(serializers.ModelSerializer):
    variant_detail = serializers.SerializerMethodField()
    product_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_detail', 'variant', 'variant_detail', 'quantity', 'unit_price', 'total_price', 'created', 'last_modified']
        read_only_fields = ['id', 'product_name', 'unit_price', 'total_price', 'created', 'last_modified']
    
    def get_variant_detail(self, obj):
        if obj.variant:
            try:
                from apps.shop.serializers import ProductVariantSerializer
                request = self.context.get('request')
                # Pass the full context to ensure nested serializers get the request
                serializer_context = self.context.copy()
                if request:
                    serializer_context['request'] = request
                
                # Serialize the variant with all its related data
                variant_serializer = ProductVariantSerializer(obj.variant, context=serializer_context)
                return variant_serializer.data
            except Exception as e:
                # Log error but don't break the response
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error serializing variant_detail for OrderItem {obj.id}: {str(e)}")
                return None
        return None
    
    def get_product_detail(self, obj):
        if obj.product:
            try:
                from apps.shop.serializers import ProductSerializer
                request = self.context.get('request')
                return ProductSerializer(obj.product, context=self.context).data
            except Exception as e:
                return None
        return None




class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address_detail = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_email', 'shipping_address', 'shipping_address_detail', 'status', 'payment_status',
            'subtotal', 'discount', 'shipping_fee', 'total_amount', 'items',
            'payment', 'placed_at', 'shipped_at', 'status_changed_at',
            'notes', 'created', 'last_modified'
        ]
        read_only_fields = ['id', 'subtotal', 'total_amount', 'placed_at', 'shipped_at', 'status_changed_at', 'created', 'last_modified']
    
    def get_shipping_address_detail(self, obj):
        from apps.user.serializers import AddressSerializer
        if obj.shipping_address:
            return AddressSerializer(obj.shipping_address).data
        return None
    
    def get_payment(self, obj):
        try:
            payment = Payment.objects.get(order=obj)
            return PaymentSerializer(payment).data
        except Payment.DoesNotExist:
            return None
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None


class CreateOrderItemSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class CreateOrderSerializer(serializers.Serializer):
    items = CreateOrderItemSerializer(many=True)
    shipping_address_id = serializers.IntegerField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    shipping_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        if not attrs.get('items'):
            raise serializers.ValidationError({"items": "Cart is empty."})
        
        # Either shipping_address_id or guest_shipping must be provided
        if not attrs.get('shipping_address_id') and not attrs.get('guest_shipping'):
            raise serializers.ValidationError("Either shipping_address_id or guest_shipping must be provided.")
        
        return attrs
    
    def validate_shipping_address_id(self, value):
        if value:
            try:
                Address.objects.get(id=value)
            except Address.DoesNotExist:
                raise serializers.ValidationError("Shipping address not found.")
        return value


# Payment Serializers
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'method', 'transaction_id', 'status', 'raw_response', 'created', 'last_modified']
        read_only_fields = ['id', 'order', 'status', 'created', 'last_modified']


class CreatePaymentSerializer(serializers.Serializer):
    method = serializers.CharField(max_length=50)
    transaction_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    raw_response = serializers.JSONField(required=False, default=dict)


# Coupon Serializers
class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'description', 'discount_percent', 'discount_amount', 
                  'valid_from', 'valid_to', 'active', 'max_uses', 'per_user_limit', 'is_valid', 
                  'created', 'last_modified']
        read_only_fields = ['id', 'created', 'last_modified']
    
    def get_is_valid(self, obj):
        return obj.is_valid()


class ValidateCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    
    def validate_code(self, value):
        try:
            coupon = Coupon.objects.get(code=value)
            if not coupon.is_valid():
                raise serializers.ValidationError("Coupon is not valid or expired.")
            return value
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Coupon not found.")


# Inventory Transaction Serializer
class InventoryTransactionSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source='product_variant.sku', read_only=True)
    
    class Meta:
        model = InventoryTransaction
        fields = ['id', 'product_variant', 'variant_sku', 'quantity', 'transaction_type', 
                  'order', 'note', 'created', 'last_modified']
        read_only_fields = ['id', 'created', 'last_modified']
