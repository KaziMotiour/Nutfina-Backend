"""
Checkout service layer.
Handles all business logic for order creation.
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from apps.user.models import Address
from apps.orders.models import Order, OrderItem, Coupon, Payment
from apps.orders.services import get_active_cart, calculate_coupon_discount


class CheckoutError(Exception):
    """Custom exception for checkout errors."""
    pass


def resolve_shipping_address(request, address_id=None, address_data=None):
    """
    Resolve shipping address based on provided data.
    
    Args:
        request: Django request object
        address_id: ID of existing address (for logged-in users)
        address_data: New address data dict
    
    Returns:
        Address instance
    
    Raises:
        CheckoutError: If address cannot be resolved
        PermissionDenied: If user tries to use someone else's address
    """
    # Case 1: Existing address ID provided
    if address_id:
        if not request.user.is_authenticated:
            raise CheckoutError("Guest users cannot use saved addresses.")
        
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            raise CheckoutError(f"Address with ID {address_id} not found.")
        
        # Verify ownership
        if address.user != request.user:
            raise PermissionDenied("You cannot use someone else's address.")
        
        return address
    
    # Case 2: New address data provided
    if address_data:
        # Validate required fields
        required_fields = ['name', 'phone', 'full_address', 'country', 'district']
        missing_fields = [field for field in required_fields if not address_data.get(field)]
        
        if missing_fields:
            raise CheckoutError(f"Missing required address fields: {', '.join(missing_fields)}")
        
        # Create new address
        address = Address.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=address_data['name'],
            phone=address_data['phone'],
            full_address=address_data['full_address'],
            country=address_data['country'],
            district=address_data['district'],
            postal_code=address_data.get('postal_code', ''),
            email=address_data.get('email', ''),
            is_default=address_data.get('is_default', False)
        )
        
        return address
    
    raise CheckoutError("No address information provided.")


def validate_cart(cart):
    """
    Validate cart before checkout.
    
    Args:
        cart: Cart instance
    
    Raises:
        CheckoutError: If cart is invalid
    """
    if not cart:
        raise CheckoutError("No active cart found.")
    
    if not cart.items.exists():
        raise CheckoutError("Cart is empty.")
    
    # Check if all items are still available
    for item in cart.items.all():
        variant = item.variant
        print('variant', variant.is_active)
        if not variant.is_active:
            raise CheckoutError(f"Product '{variant.name}' is no longer available.")
        
        # inventory = variant.inventory
        # if inventory.available < item.quantity:
        #     raise CheckoutError(
        #         f"Insufficient stock for '{variant.name}'. "
        #         f"Available: {inventory.available}, Requested: {item.quantity}"
            # )


def apply_coupon_discount(cart_subtotal, coupon_code, user):
    """
    Apply coupon discount if valid.
    
    Args:
        cart_subtotal: Decimal, cart subtotal amount
        coupon_code: str, coupon code
        user: User instance or None
    
    Returns:
        tuple: (discount_amount: Decimal, coupon: Coupon or None)
    """
    if not coupon_code:
        return Decimal('0.00'), None
    
    try:
        coupon = Coupon.objects.get(code=coupon_code, active=True)
    except Coupon.DoesNotExist:
        raise CheckoutError(f"Invalid coupon code: {coupon_code}")
    
    # Check if user can use this coupon
    can_use, message = coupon.can_be_used_by_user(user, cart_subtotal)
    if not can_use:
        raise CheckoutError(message)
    
    # Calculate discount
    discount = calculate_coupon_discount(coupon, cart_subtotal)
    
    return discount, coupon


@transaction.atomic
def create_order_from_cart(request, shipping_address, coupon=None, discount_amount=Decimal('0.00'), 
                           payment_method="COD", shipping_fee=Decimal('0.00'), notes=""):
    """
    Create order from active cart.
    
    Args:
        request: Django request object
        shipping_address: Address instance
        coupon: Coupon instance or None
        discount_amount: Decimal
        payment_method: str (used for creating Payment record)
        shipping_fee: Decimal
        notes: str
    
    Returns:
        Order instance
    
    Raises:
        CheckoutError: If order creation fails
    """
    print('create_order_from_cart')
    # Get active cart
    cart = get_active_cart(request)
    
    # Validate cart
    validate_cart(cart)
    print('validate_cart')
    
    # Calculate amounts
    subtotal = Decimal(cart.subtotal)
    discount_amount = Decimal(discount_amount)
    shipping_fee = Decimal(shipping_fee)
    
    # Calculate total amount: subtotal + shipping_fee - discount
    total_amount = subtotal + shipping_fee - discount_amount
    
    # Ensure total amount is not negative
    if total_amount < 0:
        total_amount = Decimal('0.00')
    
    # Create order with correct field names
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        shipping_address=shipping_address,
        coupon=coupon,
        coupon_code=coupon.code if coupon else "",
        subtotal=subtotal,
        discount=discount_amount,
        shipping_fee=shipping_fee,
        total_amount=total_amount,
        notes=notes or "",
        status=Order.OrderStatus.PENDING,
        payment_status=Order.PaymentStatus.PENDING
    )
    
    # Create order items from cart items
    for cart_item in cart.items.all():
        
        OrderItem.objects.create(
            order=order,
            variant=cart_item.variant,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.line_total
        )
    
    # Create payment record
    Payment.objects.create(
        order=order,
        amount=total_amount,
        method=payment_method,
        status=Payment.PaymentStatus.INITIATED if payment_method != "COD" else Payment.PaymentStatus.SUCCESS
    )
    
    # Mark cart as ordered
    cart.status = cart.STATUS_ORDERED
    cart.save()
    
    # TODO: Reserve inventory (if using inventory management)
    # reserve_stock_for_order(order, order.items.all())
    
    # TODO: Record coupon usage
    # if coupon:
    #     CouponUsage.objects.create(
    #         coupon=coupon,
    #         user=request.user if request.user.is_authenticated else None,
    #         order=order,
    #         discount_amount=discount_amount
    #     )
    
    return order


@transaction.atomic
def process_checkout(request, address_id=None, address_data=None, coupon_code=None, 
                     payment_method="COD", shipping_fee=0, notes=""):
    """
    Main checkout function - orchestrates the entire checkout flow.
    
    Args:
        request: Django request object
        address_id: int or None
        address_data: dict or None
        coupon_code: str or None
        payment_method: str
        shipping_fee: Decimal or float or int
        notes: str
    
    Returns:
        Order instance
    
    Raises:
        CheckoutError: If checkout fails
        PermissionDenied: If user tries unauthorized action
    """
    # Step 1: Resolve shipping address
    shipping_address = resolve_shipping_address(request, address_id, address_data)
    
    # Step 2: Get and validate cart
    cart = get_active_cart(request)
    print('cart', cart)
    validate_cart(cart)
    print('validate_cart', validate_cart(cart))
    
    # Step 3: Apply coupon discount if provided
    cart_subtotal = Decimal(cart.subtotal)
    discount_amount, coupon = apply_coupon_discount(
        cart_subtotal, 
        coupon_code, 
        request.user if request.user.is_authenticated else None
    )
    
    # Step 4: Create order
    order = create_order_from_cart(
        request=request,
        shipping_address=shipping_address,
        coupon=coupon,
        discount_amount=discount_amount,
        payment_method=payment_method,
        shipping_fee=Decimal(str(shipping_fee)),
        notes=notes
    )
    
    return order
