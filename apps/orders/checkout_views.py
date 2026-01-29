"""
Checkout API views.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.exceptions import PermissionDenied

from .checkout_serializers import CheckoutRequestSerializer
from .checkout_service import process_checkout, CheckoutError
from .serializers import OrderSerializer


class CheckoutView(APIView):
    """
    Handle checkout request for both authenticated and guest users.
    
    POST /api/orders/checkout/
    
    Request body examples:
    
    1. Logged-in user with existing address:
    {
        "address_id": 123,
        "coupon_code": "SAVE10",
        "payment_method": "COD",
        "notes": "Please call before delivery"
    }
    
    2. Logged-in user with new address OR guest user:
    {
        "address": {
            "name": "John Doe",
            "phone": "01712345678",
            "full_address": "123 Main St, Apt 4B",
            "country": "BD",
            "district": "Dhaka",
            "postal_code": "1000",
            "email": "john@example.com"
        },
        "coupon_code": "SAVE10",
        "payment_method": "COD",
        "notes": "Please call before delivery"
    }
    
    Success Response (201):
    {
        "success": true,
        "message": "Order placed successfully",
        "order": { ... order details ... }
    }
    
    Error Response (400):
    {
        "success": false,
        "error": "Error message"
    }
    """
    permission_classes = [AllowAny]  # Allow both authenticated and guest users
    
    def post(self, request):
        # Validate request data
        serializer = CheckoutRequestSerializer(data=request.data)
        print(serializer.is_valid())
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": "Invalid request data",
                    "details": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        
        try:
            # Process checkout
            order = process_checkout(
                request=request,
                address_id=validated_data.get('address_id'),
                address_data=validated_data.get('address'),
                coupon_code=validated_data.get('coupon_code'),
                payment_method=validated_data.get('payment_method', 'COD'),
                shipping_fee=validated_data.get('shipping_fee', 0),
                notes=validated_data.get('notes', '')
            )
            
            # Serialize order response
            order_serializer = OrderSerializer(order)
            
            return Response(
                {
                    "success": True,
                    "message": "Order placed successfully",
                    "order": order_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        except CheckoutError as e:
            return Response(
                {
                    "success": False,
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except PermissionDenied as e:
            return Response(
                {
                    "success": False,
                    "error": str(e)
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        except Exception as e:
            # Log the error in production
            print(f"Checkout error: {str(e)}")
            
            return Response(
                {
                    "success": False,
                    "error": "An unexpected error occurred during checkout. Please try again."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
