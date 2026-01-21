from django.urls import path
from .views import (
    # Cart views
    CartView, AddToCartView, UpdateCartItemView, RemoveFromCartView,
    # Order views
    OrderListView, OrderDetailView, CheckoutView, OrderStatusUpdateView,
    # Payment views
    PaymentDetailView, CreatePaymentView, UpdatePaymentStatusView,
    # Coupon views
    CouponListView, ValidateCouponView,
)

urlpatterns = [
    # Cart endpoints
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='cart-add'),
    path('cart/items/<int:pk>/', UpdateCartItemView.as_view(), name='cart-item-update'),
    path('cart/items/<int:pk>/remove/', RemoveFromCartView.as_view(), name='cart-item-remove'),
    
    # Order endpoints
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/<int:pk>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    
    # Payment endpoints
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/create/', CreatePaymentView.as_view(), name='payment-create'),
    path('payments/<int:pk>/status/', UpdatePaymentStatusView.as_view(), name='payment-status-update'),
    
    # Coupon endpoints
    path('coupons/', CouponListView.as_view(), name='coupon-list'),
    path('coupons/validate/', ValidateCouponView.as_view(), name='coupon-validate'),
]
