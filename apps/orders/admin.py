from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Cart, CartItem, Order, OrderItem, Payment,
    InventoryTransaction, Coupon, CouponUsage
)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'status', 'subtotal', 'item_count', 'created')
    list_filter = ('created', 'last_modified')
    search_fields = ('user__email', 'user__full_name', 'user__phone')
    readonly_fields = ('created', 'last_modified', 'subtotal', 'item_count')
    date_hierarchy = 'created'
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'session_key', 'status', 'subtotal')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('variant', 'quantity', 'unit_price', 'line_total', 'created')
    can_delete = False
    fields = ('variant', 'quantity', 'unit_price', 'line_total', 'created')
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'variant', 'quantity', 'unit_price', 'line_total', 'created')
    list_filter = ('created', 'last_modified')
    search_fields = ('cart__user__email', 'variant__sku', 'variant__product__name')
    readonly_fields = ('line_total', 'created', 'last_modified')
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Item Information', {
            'fields': ('cart', 'variant', 'quantity', 'unit_price', 'line_total')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'variant', 'quantity', 'unit_price', 'total_price')
    can_delete = False
    fields = ('product', 'product_name', 'variant', 'quantity', 'unit_price', 'total_price')
    
    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ('order', 'amount', 'method', 'transaction_id', 'status', 'raw_response', 'created', 'last_modified')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_number', 'user_display', 'status', 'payment_status',
        'total_amount', 'item_count', 'placed_at', 'status_changed_at',
    )
    list_filter = ('status', 'payment_status', 'placed_at', 'status_changed_at')
    search_fields = (
        'id', 'user__email', 'user__full_name', 'user__phone',
    )
    readonly_fields = (
        'id', 'subtotal', 'total_amount', 'placed_at', 'status_changed_at',
        'shipped_at', 'created', 'last_modified'
    )
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'order_number', 'user', 'status', 'status_changed_at', 'placed_at', 'shipped_at')
        }),
        # ('Shipping Information', {
        #     'fields': ('shipping_address', 'shipping_address_display')
        # }),
        ('Coupon Information', {
            'fields': ('coupon', 'coupon_code')
        }),
        ('Payment Information', {
            'fields': ('payment_status',)
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'shipping_fee', 'discount', 'total_amount')
        }),
       
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
        ('Address Information', {
            'fields': ('shipping_address',)
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    
    def order_number(self, obj):
        return f"#{obj.id}"
    order_number.short_description = 'Order #'
    
    def user_display(self, obj):
        if obj.user:
            url = reverse('admin:user_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    user_display.short_description = 'Customer'
    
    def shipping_address_display(self, obj):
        if obj.shipping_address:
            addr = obj.shipping_address
            return format_html(
                '<strong>{}</strong><br/>{}<br/>{}<br/>Phone: {}',
                addr.name or addr.user.full_name,
                addr.full_address,
                f"{addr.district}, {addr.country}",
                addr.phone
            )
        return '-'
    shipping_address_display.short_description = 'Shipping Address'
    
    def coupon_display(self, obj):
        if obj.coupon:
            usage_count = obj.coupon.get_usage_count()
            max_uses_text = f" / {obj.coupon.max_uses}" if obj.coupon.max_uses else ""
            return format_html(
                '<strong>{}</strong><br/>Discount: {}<br/>Usage: {}{}',
                obj.coupon.code,
                f"{obj.coupon.discount_percent}%" if obj.coupon.discount_percent else f"${obj.coupon.discount_amount}",
                usage_count,
                max_uses_text
            )
        return '-'
    coupon_display.short_description = 'Coupon Details'
    
    def payment_display(self, obj):
        if hasattr(obj, 'payment'):
            payment = obj.payment
            status_color = {
                'success': 'green',
                'failed': 'red',
                'initiated': 'orange',
                'refunded': 'gray'
            }.get(payment.status, 'black')
            return format_html(
                '<span style="color: {};"><strong>{}</strong></span><br/>'
                'Method: {}<br/>Amount: {}<br/>Transaction ID: {}',
                status_color,
                payment.get_status_display(),
                payment.method,
                payment.amount,
                payment.transaction_id or 'N/A'
            )
        return '-'
    payment_display.short_description = 'Payment Details'
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status=Order.OrderStatus.CONFIRMED)
    mark_as_confirmed.short_description = 'Mark selected orders as Confirmed'
    
    def mark_as_processing(self, request, queryset):
        queryset.update(status=Order.OrderStatus.PROCESSING)
    mark_as_processing.short_description = 'Mark selected orders as Processing'
    
    def mark_as_shipped(self, request, queryset):
        queryset.update(status=Order.OrderStatus.SHIPPED, shipped_at=timezone.now())
    mark_as_shipped.short_description = 'Mark selected orders as Shipped'
    
    def mark_as_delivered(self, request, queryset):
        queryset.update(status=Order.OrderStatus.DELIVERED)
    mark_as_delivered.short_description = 'Mark selected orders as Delivered'
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status=Order.OrderStatus.CANCELLED)
    mark_as_cancelled.short_description = 'Mark selected orders as Cancelled'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product_name', 'variant_sku', 'quantity', 'unit_price', 'total_price', 'created')
    list_filter = ('created', 'last_modified')
    search_fields = ('order__id', 'product_name', 'variant__sku', 'variant__product__name')
    readonly_fields = ('order', 'product', 'product_name', 'variant', 'quantity', 'unit_price', 'total_price', 'created', 'last_modified')
    date_hierarchy = 'created'
    
    def variant_sku(self, obj):
        return obj.variant.sku if obj.variant else 'N/A'
    variant_sku.short_description = 'SKU'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order',)
        }),
        ('Product Information', {
            'fields': ('product', 'product_name', 'variant')
        }),
        ('Pricing', {
            'fields': ('quantity', 'unit_price', 'total_price')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'method', 'amount', 'status', 'transaction_id', 'created')
    list_filter = ('status', 'method', 'created', 'last_modified')
    search_fields = ('order__id', 'transaction_id', 'order__user__email')
    readonly_fields = ('order', 'amount', 'method', 'transaction_id', 'status', 'raw_response', 'created', 'last_modified')
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'amount', 'method', 'status', 'transaction_id')
        }),
        ('Raw Response', {
            'fields': ('raw_response',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_variant', 'transaction_type', 'quantity', 'order', 'note', 'created')
    list_filter = ('transaction_type', 'created', 'last_modified')
    search_fields = ('product_variant__sku', 'product_variant__product__name', 'order__id', 'note')
    readonly_fields = ('created', 'last_modified')
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('product_variant', 'transaction_type', 'quantity', 'order', 'note')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_display', 'valid_from', 'valid_to',
        'active', 'is_valid_now', 'usage_display', 'max_uses', 'per_user_limit', 'created'
    )
    list_filter = ('active', 'valid_from', 'valid_to', 'created')
    search_fields = ('code', 'description')
    readonly_fields = ('created', 'last_modified', 'is_valid_now', 'usage_count_display')
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Coupon Information', {
            'fields': ('code', 'description', 'active')
        }),
        ('Discount Settings', {
            'fields': ('discount_percent', 'discount_amount', 'max_discount'),
            'description': 'Enter either discount_percent OR discount_amount, not both. Max_discount only applies to percentage discounts.'
        }),
        ('Order Requirements', {
            'fields': ('min_order_amount',),
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to', 'is_valid_now')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'per_user_limit', 'usage_count_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def discount_display(self, obj):
        if obj.discount_percent:
            return f"{obj.discount_percent}%"
        elif obj.discount_amount:
            return f"${obj.discount_amount}"
        return '-'
    discount_display.short_description = 'Discount'
    
    def is_valid_now(self, obj):
        return obj.is_valid()
    is_valid_now.boolean = True
    is_valid_now.short_description = 'Valid Now'
    
    def usage_count_display(self, obj):
        count = obj.get_usage_count()
        if obj.max_uses:
            return f"{count} / {obj.max_uses}"
        return str(count)
    usage_count_display.short_description = 'Total Usage'
    
    def usage_display(self, obj):
        count = obj.get_usage_count()
        if obj.max_uses:
            percentage = (count / obj.max_uses) * 100
            color = 'green' if percentage < 75 else 'orange' if percentage < 100 else 'red'
            return format_html(
                '<span style="color: {};">{} / {}</span>',
                color, count, obj.max_uses
            )
        return str(count)
    usage_display.short_description = 'Usage'


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('id', 'coupon', 'order_link', 'user_display', 'discount_applied', 'created')
    list_filter = ('created', 'last_modified')
    search_fields = ('coupon__code', 'order__id', 'user__email', 'user__full_name')
    readonly_fields = ('coupon', 'order', 'user', 'discount_applied', 'created', 'last_modified')
    date_hierarchy = 'created'
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.pk])
            return format_html('<a href="{}">Order #{}</a>', url, obj.order.id)
        return '-'
    order_link.short_description = 'Order'
    
    def user_display(self, obj):
        if obj.user:
            url = reverse('admin:user_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return 'Guest'
    user_display.short_description = 'User'
    
    fieldsets = (
        ('Usage Information', {
            'fields': ('coupon', 'order', 'user', 'discount_applied')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Coupon usage is automatically created when orders are placed
        return False