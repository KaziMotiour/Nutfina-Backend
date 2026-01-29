"""
Serializers for checkout flow.
Separate from main serializers to keep checkout logic clean.
"""
from rest_framework import serializers
from apps.user.models import Address


class CheckoutAddressSerializer(serializers.Serializer):
    """
    Serializer for new address data during checkout.
    Used when user provides new address (not selecting existing one).
    """
    name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=32)
    full_address = serializers.CharField(max_length=500)
    country = serializers.CharField(max_length=2)  # ISO2 country code
    district = serializers.CharField(max_length=120)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    is_default = serializers.BooleanField(default=False)


class CheckoutRequestSerializer(serializers.Serializer):
    """
    Validates checkout request data.
    Either address_id (existing) OR address (new) must be provided.
    """
    # Option 1: Use existing address (logged-in users only)
    address_id = serializers.IntegerField(required=False, allow_null=True)
    
    # Option 2: Provide new address data
    address = CheckoutAddressSerializer(required=False, allow_null=True)
    
    # Optional: Coupon code
    coupon_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    # Payment method
    payment_method = serializers.CharField(max_length=20, default="COD")
    
    # Shipping fee (default 0 for free shipping)
    shipping_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    
    # Optional: Order notes
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, data):
        """
        Ensure either address_id or address is provided, but not both.
        """
        address_id = data.get('address_id')
        address_data = data.get('address')
        
        if not address_id and not address_data:
            raise serializers.ValidationError(
                "Either 'address_id' or 'address' must be provided."
            )
        
        if address_id and address_data:
            raise serializers.ValidationError(
                "Provide either 'address_id' or 'address', not both."
            )
        
        return data
