from decimal import Decimal
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.shop.models import ProductVariant, Inventory
from apps.user.models import Address
from .models import (
    InventoryTransaction, Order, OrderItem, 
    Payment, Coupon, Cart, CartItem
)


class InventoryError(Exception):
    pass

def get_active_cart(request):
    """Get active cart for user or session. Automatically merges session cart if user is authenticated."""
    print("get_active_cart", request.user.is_authenticated)
    if request.user.is_authenticated:
        # Check if there's a session cart to merge
        print("session key", request.session.session_key)
        if request.session.session_key:
            guest_cart = Cart.objects.filter(
                session_key=request.session.session_key,
                status=Cart.STATUS_ACTIVE
            ).first()
            
            user_cart, _ = Cart.objects.get_or_create(
                user=request.user,
                status=Cart.STATUS_ACTIVE
            )
            
            # Merge guest cart into user cart if it exists
            if guest_cart and guest_cart.id != user_cart.id:
                for item in guest_cart.items.all():
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=user_cart,
                        variant=item.variant,
                        defaults={
                            "quantity": item.quantity,
                            "unit_price": item.unit_price,
                        }
                    )
                    if not created:
                        cart_item.quantity += item.quantity
                        cart_item.save()
                
                # Update cart subtotal
                update_cart_subtotal(user_cart)
                # Delete guest cart
                guest_cart.delete()
            
            return user_cart
        else:
            # No session cart, just get/create user cart
            print("No session cart, just get/create user cart")
            print(request.user)
            cart, _ = Cart.objects.get_or_create(
                user=request.user,
                status=Cart.STATUS_ACTIVE
            )
            return cart
        
    
    print("session key", request.session.session_key)
    
    if not request.session.session_key:
        print("No session key, create new session")
        request.session.create()
        # Set a flag to mark session as modified so it gets saved and cookie is sent
        request.session['_cart_session_initialized'] = True

    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key,
        status=Cart.STATUS_ACTIVE
    )
    return cart


def _get_inventory_for_variant_for_update(variant_id):
    return Inventory.objects.select_for_update().select_related('variant').get(variant_id=variant_id)


@transaction.atomic
def reserve_stock_for_order(order, items):
    """
    items: list of dicts [{variant: ProductVariant, quantity: int}, ...]
    Creates RESERVE transactions (negative quantity) and ensures available stock.
    """
    for it in items:
        variant = it['variant']
        qty = int(it['quantity'])
        try:
            inv = Inventory.objects.select_for_update().get(variant=variant)
            # Available = quantity - reserved (reserved computed via transactions)
            if inv.available < qty:
                raise InventoryError(f"Insufficient stock for SKU {variant.sku}. Available {inv.available}, requested {qty}")
            # Create reserve transaction: record negative qty to indicate reserved reduction
            InventoryTransaction.objects.create(
                product_variant=variant,
                quantity=-qty,
                transaction_type=InventoryTransaction.TransactionType.RESERVE,
                order=order,
                note=f"Reserve for order {order.id}"
            )
        except Inventory.DoesNotExist:
            # No inventory tracking for this variant, skip
            pass
    return True


@transaction.atomic
def release_reserved_stock(order):
    """
    Release all RESERVE transactions related to this order by creating RELEASE transaction(s) (+qty)
    """
    reserves = InventoryTransaction.objects.filter(
        order=order, 
        transaction_type=InventoryTransaction.TransactionType.RESERVE
    )
    for r in reserves:
        InventoryTransaction.objects.create(
            product_variant=r.product_variant,
            quantity=abs(r.quantity),  # positive
            transaction_type=InventoryTransaction.TransactionType.RELEASE,
            order=order,
            note=f"Release for order {order.id}"
        )
    return True


@transaction.atomic
def commit_sale_stock(order):
    """
    Convert RESERVE -> SALE by adding SALE transaction (negative qty)
    """
    reserves = InventoryTransaction.objects.filter(
        order=order, 
        transaction_type=InventoryTransaction.TransactionType.RESERVE
    )
    if not reserves.exists():
        # If no reserves (maybe previous flow didn't reserve), ensure availability and subtract
        for item in order.items.select_related('variant').all():
            if item.variant:
                try:
                    qty = item.quantity
                    inv = Inventory.objects.select_for_update().get(variant=item.variant)
                    if inv.available < qty:
                        raise InventoryError(f"Insufficient stock for SKU {item.variant.sku} to commit sale.")
                    InventoryTransaction.objects.create(
                        product_variant=item.variant,
                        quantity=-qty,
                        transaction_type=InventoryTransaction.TransactionType.SALE,
                        order=order,
                        note=f"Sale for order {order.id}"
                    )
                except Inventory.DoesNotExist:
                    pass
        return True

    # If reserves exist, create SALE transactions
    for r in reserves:
        qty = abs(r.quantity)
        InventoryTransaction.objects.create(
            product_variant=r.product_variant,
            quantity=-qty,
            transaction_type=InventoryTransaction.TransactionType.SALE,
            order=order,
            note=f"Sale for order {order.id}"
        )
    return True


@transaction.atomic
def adjust_inventory(variant, delta, note="manual adjustment"):
    inv, _ = Inventory.objects.select_for_update().get_or_create(variant=variant)
    InventoryTransaction.objects.create(
        product_variant=variant,
        quantity=delta,
        transaction_type=InventoryTransaction.TransactionType.ADJUSTMENT,
        note=note
    )
    inv.quantity = F('quantity') + delta
    inv.save()
    inv.refresh_from_db()
    return inv


@transaction.atomic
def create_order_from_cart(user, cart_items, shipping_address_id=None, guest_shipping=None, 
                          payment_method=None, coupon_code=None, shipping_fee=Decimal('0.00'), notes=''):
    """
    cart_items: list of {variant_id, quantity, unit_price} from validated cart
    shipping_address_id: ID of user's Address (if authenticated user)
    payment_method: string or None (for COD etc.)
    coupon_code: optional coupon code
    shipping_fee: shipping fee amount
    notes: order notes
    """
    # Validate and lock all variant inventory rows first
    variant_ids = [ci['variant_id'] for ci in cart_items]
    variants = ProductVariant.objects.select_related('product').filter(id__in=variant_ids, is_active=True)
    variants_map = {v.id: v for v in variants}
    if len(variants_map) != len(set(variant_ids)):
        raise ValidationError("One or more variants not found or inactive.")

    # Compute totals
    subtotal = Decimal('0.00')
    items_payload = []
    for ci in cart_items:
        v = variants_map[ci['variant_id']]
        qty = int(ci['quantity'])
        unit_price = Decimal(ci.get('unit_price') or str(v.final_price))
        total_price = (unit_price * qty).quantize(Decimal("0.01"))
        subtotal += total_price
        items_payload.append({
            "variant": v,
            "quantity": qty,
            "unit_price": unit_price,
            "total_price": total_price
        })

    # Validate coupon if provided
    coupon = None
    discount = Decimal('0.00')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            if not coupon.is_valid():
                raise ValidationError("Coupon is not valid")
            # Calculate discount
            if coupon.discount_percent:
                discount = (subtotal * coupon.discount_percent / 100).quantize(Decimal("0.01"))
            elif coupon.discount_amount:
                discount = min(coupon.discount_amount, subtotal)
        except Coupon.DoesNotExist:
            raise ValidationError("Coupon not found")

    # Get shipping address
    shipping_address = None
    if shipping_address_id:
        try:
            shipping_address = Address.objects.get(id=shipping_address_id, user=user)
        except Address.DoesNotExist:
            raise ValidationError("Shipping address not found")

    # Create order
    order = Order.objects.create(
        user=user,
        shipping_address=shipping_address,
        subtotal=subtotal,
        discount=discount,
        shipping_fee=Decimal(str(shipping_fee)),
        notes=notes,
    )
    order.calculate_totals()
    order.save()

    # Create order items (snapshots)
    order_items = []
    for ip in items_payload:
        v = ip['variant']
        oi = OrderItem.objects.create(
            order=order,
            product=v.product,
            product_name=v.product.name,
            variant=v,
            quantity=ip['quantity'],
            unit_price=ip['unit_price'],
            total_price=ip['total_price'],
        )
        order_items.append(oi)

    # Reserve stock (throws InventoryError if insufficient)
    reserve_input = [{"variant": oi.variant, "quantity": oi.quantity} for oi in order_items if oi.variant]
    if reserve_input:
        reserve_stock_for_order(order, reserve_input)

    # Create payment record if payment initiated
    if payment_method:
        Payment.objects.create(
            order=order,
            amount=order.total_amount,
            method=payment_method,
            status=Payment.PaymentStatus.INITIATED
        )

    return order


@transaction.atomic
def get_or_create_cart(user):
    """Get or create active cart for user"""
    cart, created = Cart.objects.get_or_create(
        user=user,
        active=True,
        defaults={'subtotal': Decimal('0.00')}
    )
    return cart


@transaction.atomic
def add_to_cart(request, variant_id, quantity):
    """Add item to cart or update quantity if exists"""
    try:
        print(variant_id)
        variant = ProductVariant.objects.get(id=variant_id, is_active=True)
        
    except ProductVariant.DoesNotExist:
        raise ValidationError("Product variant not found or inactive")
    
    # Check inventory
    # try:
    #     inv = Inventory.objects.get(variant=variant)
    #     if inv.available < quantity:
    #         raise InventoryError(f"Insufficient stock. Available: {inv.available}")
    # except Inventory.DoesNotExist:
    #     pass  # No inventory tracking
    
    cart = get_active_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={
            'quantity': quantity,
            'unit_price': variant.final_price
        }
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    # Update cart subtotal
    update_cart_subtotal(cart)
    return cart_item


@transaction.atomic
def update_cart_item(cart_item, quantity):
    """Update cart item quantity"""
    if quantity <= 0:
        cart_item.delete()
        return None
    
    # Check inventory
    # try:
    #     inv = Inventory.objects.get(variant=cart_item.variant)
    #     if inv.available < quantity:
    #         raise InventoryError(f"Insufficient stock. Available: {inv.available}")
    # except Inventory.DoesNotExist:
    #     pass
    
    cart_item.quantity = quantity
    cart_item.save()
    
    # Update cart subtotal
    update_cart_subtotal(cart_item.cart)
    return cart_item


@transaction.atomic
def remove_from_cart(cart_item):
    """Remove item from cart"""
    cart = cart_item.cart
    cart_item.delete()
    update_cart_subtotal(cart)


def update_cart_subtotal(cart):
    """Recalculate cart subtotal"""
    cart.subtotal = cart.items.aggregate(Sum(F('line_total')))['line_total__sum'] or Decimal('0.00')
    cart.save()
    
    
def merge_cart(request, user):
    session_key = request.session.session_key

    guest_cart = Cart.objects.filter(
        session_key=session_key,
        status=Cart.STATUS_ACTIVE
    ).first()

    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(
        user=user,
        status=Cart.STATUS_ACTIVE
    )

    for item in guest_cart.items.all():
        cart_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            variant=item.variant,
            defaults={
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
        )
        if not created:
            cart_item.quantity += item.quantity
            cart_item.save()

    guest_cart.delete()


def calculate_coupon_discount(coupon, subtotal):
    """Calculate discount amount from coupon"""
    if coupon.discount_percent:
        return (subtotal * coupon.discount_percent / 100).quantize(Decimal("0.01"))
    elif coupon.discount_amount:
        return min(coupon.discount_amount, subtotal)
    return Decimal('0.00')
