# apps/orders/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Order
from .services import commit_sale_stock, release_reserved_stock
from django.db import transaction

@receiver(post_save, sender=Payment)
def handle_payment_change(sender, instance: Payment, created, **kwargs):
    # On payment success → commit stock and set order/payment status appropriately
    if instance.status == Payment.PaymentStatus.SUCCESS:
        order = instance.order
        # idempotent commit: wrap in transaction and catch InventoryError at view layer
        with transaction.atomic():
            try:
                commit_sale_stock(order)
                order.payment_status = Order.PaymentStatus.PAID
                order.status = Order.OrderStatus.CONFIRMED
                order.save()
            except Exception as e:
                # log and re-raise or handle accordingly
                raise

@receiver(post_save, sender=Order)
def order_status_changed(sender, instance: Order, created, **kwargs):
    # If order canceled, release reserved stock
    if instance.status == Order.OrderStatus.CANCELLED:
        release_reserved_stock(instance)
