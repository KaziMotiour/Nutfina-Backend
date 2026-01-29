from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.core.exceptions import ValidationError

from .models import Cart, CartItem, Order, Payment, Coupon
from .serializers import (
    CartSerializer, CartItemSerializer, AddToCartSerializer, UpdateCartItemSerializer,
    OrderSerializer, CreateOrderSerializer, OrderItemSerializer,
    PaymentSerializer, CreatePaymentSerializer,
    CouponSerializer, ValidateCouponSerializer
)
from .services import (
    add_to_cart, update_cart_item, remove_from_cart, create_order_from_cart,
    get_active_cart, InventoryError, calculate_coupon_discount
)



# Cart Views
class CartView(generics.RetrieveAPIView):
    """Get current user's or session's active cart"""
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        cart = get_active_cart(self.request)
        return cart
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class AddToCartView(generics.CreateAPIView):
    """Add item to cart (works for authenticated users and guests via session)"""
    serializer_class = AddToCartSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        print(serializer.is_valid())
        serializer.is_valid(raise_exception=True)
        
        print(serializer.validated_data)
        try:
            add_to_cart(
                request=request,
                variant_id=serializer.validated_data['variant_id'],
                quantity=serializer.validated_data['quantity']
            )
            # Return full cart to update frontend state
            cart = get_active_cart(request)
            return Response(
                CartSerializer(cart).data,
                status=status.HTTP_201_CREATED
            )
        except InventoryError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UpdateCartItemView(generics.UpdateAPIView):
    """Update cart item quantity"""
    serializer_class = UpdateCartItemSerializer
    permission_classes = [permissions.AllowAny]
    queryset = CartItem.objects.all()
    
    def get_queryset(self):
        cart = get_active_cart(self.request)
        return CartItem.objects.filter(cart=cart)
    
    def update(self, request, *args, **kwargs):
        cart_item = self.get_object()
        serializer = self.get_serializer(
            data=request.data,
            context={'cart_item': cart_item}
        )
        serializer.is_valid(raise_exception=True)
        try:
            update_cart_item(
                cart_item=cart_item,
                quantity=serializer.validated_data['quantity']
            )
            # Return full cart
            cart = get_active_cart(request)
            return Response(CartSerializer(cart).data)
        except InventoryError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class RemoveFromCartView(generics.DestroyAPIView):
    """Remove item from cart"""
    permission_classes = [permissions.AllowAny]
    queryset = CartItem.objects.all()
    
    def get_queryset(self):
        cart = get_active_cart(self.request)
        return CartItem.objects.filter(cart=cart)
    
    def destroy(self, request, *args, **kwargs):
        cart_item = self.get_object()
        remove_from_cart(cart_item)
        # Return updated cart
        cart = get_active_cart(request)
        return Response(CartSerializer(cart).data)


# Order Views
class OrderListView(generics.ListAPIView):
    """List user's orders"""
    serializer_class = OrderSerializer
    # permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status']
    ordering_fields = ['created', 'placed_at', 'total_amount']
    ordering = ['-created']
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'items',
            'items__variant',
        )
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class OrderDetailView(generics.RetrieveAPIView):
    """
    Get order details - public access by order_number, restricted access by ID.
    - When order_number is provided: Anyone can access the invoice (public invoice link)
    - When ID (pk) is provided: Only the order owner or staff can access
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'pk'
    
    def get_queryset(self):
        """
        Base queryset - only used for ID-based lookups.
        For order_number lookups, we bypass this and query directly.
        """
        if self.request.user.is_authenticated:
            # Authenticated users can view their own orders
            return Order.objects.filter(user=self.request.user)
        else:
            # Guest users can view orders with user=None (guest orders)
            return Order.objects.filter(user=None)
    
    def get_object(self):
        """
        Override to support lookup by both ID (pk) and order_number.
        - order_number: Public access - anyone with the order_number can view
        - pk (ID): Restricted access - only order owner or staff can view
        """
        from rest_framework.exceptions import NotFound
        
        # Check if order_number is provided in URL (public invoice access)
        order_number = self.kwargs.get('order_number')
        if order_number:
            # Public access by order_number - no authentication required
            try:
                return Order.objects.get(order_number=order_number, deleted=False)
            except Order.DoesNotExist:
                raise NotFound("Order not found")
        
        # Default lookup by pk (ID) - restricted access
        pk = self.kwargs.get('pk')
        if pk:
            queryset = self.get_queryset()
            try:
                return queryset.get(pk=pk, deleted=False)
            except Order.DoesNotExist:
                # Check if user is staff (staff can view any order)
                if self.request.user.is_authenticated and self.request.user.is_staff:
                    try:
                        return Order.objects.get(pk=pk, deleted=False)
                    except Order.DoesNotExist:
                        pass
                raise NotFound("Order not found")
        
        return super().get_object()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CheckoutView(APIView):
    """Create order from cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Get cart items
        try:
            cart = get_active_cart(request)
            cart_items = [
                {
                    'variant_id': item.variant.id,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price)
                }
                for item in cart.items.all()
            ]
        except Cart.DoesNotExist:
            return Response(
                {"detail": "Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart_items:
            return Response(
                {"detail": "Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = create_order_from_cart(
                user=request.user,
                cart_items=cart_items,
                shipping_address_id=data.get('shipping_address_id'),
                guest_shipping=data.get('guest_shipping'),
                payment_method=data.get('payment_method'),
                coupon_code=data.get('coupon_code'),
                shipping_fee=data.get('shipping_fee', 0),
                notes=data.get('notes', '')
            )
            
            # Deactivate cart after order creation
            cart.status = Cart.STATUS_ORDERED
            cart.save()
            
            return Response(
                OrderSerializer(order, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except InventoryError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class OrderStatusUpdateView(generics.UpdateAPIView):
    """Update order status (admin only)"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Order.objects.all()
    
    def partial_update(self, request, *args, **kwargs):
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status and new_status in [choice[0] for choice in Order.OrderStatus.choices]:
            order.status = new_status
            if new_status == Order.OrderStatus.SHIPPED:
                from django.utils import timezone
                order.shipped_at = timezone.now()
            order.save()
            return Response(OrderSerializer(order, context={'request': request}).data)
        
        return Response(
            {"detail": "Invalid status."},
            status=status.HTTP_400_BAD_REQUEST
        )


# Payment Views
class PaymentDetailView(generics.RetrieveAPIView):
    """Get payment details"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(order__user=self.request.user)


class CreatePaymentView(generics.CreateAPIView):
    """Create payment record"""
    serializer_class = CreatePaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        order_id = request.data.get('order_id')
        if not order_id:
            return Response(
                {"detail": "order_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'amount': order.total_amount,
                'method': serializer.validated_data['method'],
                'transaction_id': serializer.validated_data.get('transaction_id', ''),
                'status': Payment.PaymentStatus.INITIATED,
                'raw_response': serializer.validated_data.get('raw_response', {})
            }
        )
        
        if not created:
            payment.method = serializer.validated_data['method']
            payment.transaction_id = serializer.validated_data.get('transaction_id', '')
            payment.raw_response = serializer.validated_data.get('raw_response', {})
            payment.save()
        
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class UpdatePaymentStatusView(generics.UpdateAPIView):
    """Update payment status (for webhooks or admin)"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Payment.objects.all()
    
    def partial_update(self, request, *args, **kwargs):
        payment = self.get_object()
        new_status = request.data.get('status')
        
        if new_status and new_status in [choice[0] for choice in Payment.PaymentStatus.choices]:
            payment.status = new_status
            payment.save()
            return Response(PaymentSerializer(payment).data)
        
        return Response(
            {"detail": "Invalid status."},
            status=status.HTTP_400_BAD_REQUEST
        )


# Coupon Views
class CouponListView(generics.ListAPIView):
    """List all active coupons"""
    serializer_class = CouponSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Coupon.objects.filter(active=True)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['active']


class ValidateCouponView(APIView):
    """Validate and apply coupon code"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ValidateCouponSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        subtotal = serializer.validated_data.get('subtotal', 0)
        
        try:
            coupon = Coupon.objects.get(code=code, active=True)
            print(coupon)
            # Get user if authenticated
            user = request.user if request.user.is_authenticated else None
            
            # Check if coupon can be used
            can_use, message = coupon.can_be_used_by_user(user, subtotal)
            if not can_use:
                return Response(
                    {"valid": False, "detail": message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate discount
            discount = calculate_coupon_discount(coupon, subtotal)
            
            return Response({
                "valid": True,
                "coupon": CouponSerializer(coupon).data,
                "discount": float(discount),
                "discount_amount": float(discount),
                "message": "Coupon applied successfully",
                "code": code
            })
        except Coupon.DoesNotExist:
            return Response(
                {"valid": False, "detail": "Coupon not found."},
                status=status.HTTP_404_NOT_FOUND
            )
