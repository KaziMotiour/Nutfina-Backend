from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from .models import (
    Categories, Products, ProductImages, ProductVariant,
    ProductVariantImage, Inventory, ProductRating
)


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'product_count', 'created', 'last_modified')
    list_filter = ('is_active', 'created', 'last_modified')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created', 'last_modified')
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def product_count(self, obj):
        count = obj.products_set.count()
        if count > 0:
            url = reverse('admin:shop_products_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    product_count.short_description = 'Products'


class ProductImagesInline(admin.TabularInline):
    model = ProductImages
    extra = 3
    fields = ('image', 'alt_text', 'ordering', 'is_active')
    ordering = ('ordering', 'id')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'base_price', 'is_active', 'is_featured',
        'image_preview', 'variant_count', 'created', 'last_modified'
    )
    list_filter = ('category', 'is_active', 'is_featured', 'created', 'last_modified')
    search_fields = ('name', 'slug', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created', 'last_modified', 'image_preview', 'variant_count')
    date_hierarchy = 'created'
    inlines = [ProductImagesInline]
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'category', 'excerpt', 'description')
        }),
        ('Pricing', {
            'fields': ('base_price',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('variant_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        print(obj)
        first_image = obj.productimages_set.filter(is_active=True).order_by('ordering', 'id').first()
        if first_image and first_image.image:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; object-fit: cover;" />',
                first_image.image.url
            )
        return '-'
    image_preview.short_description = 'Image'
    
    def variant_count(self, obj):
        count = obj.productvariant_set.count()
        if count > 0:
            url = reverse('admin:shop_productvariant_changelist') + f'?product__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    variant_count.short_description = 'Variants'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('category')


@admin.register(ProductImages)
class ProductImagesAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'image_preview', 'alt_text', 'ordering', 'is_active', 'created')
    list_filter = ('is_active', 'created', 'last_modified')
    search_fields = ('product__name', 'product__slug', 'alt_text')
    list_editable = ('ordering', 'is_active')
    readonly_fields = ('created', 'last_modified', 'image_preview')
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Image Information', {
            'fields': ('product', 'image', 'image_preview', 'alt_text', 'ordering', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px; object-fit: cover;" />',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Preview'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')


class ProductVariantImageInline(admin.TabularInline):
    model = ProductVariantImage
    extra = 2
    fields = ('image', 'ordering', 'is_active')
    ordering = ('ordering', 'id')


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0
    max_num = 1
    can_delete = False
    fields = ('quantity', 'low_stock_threshold', 'available', 'reserved')
    readonly_fields = ('available', 'reserved')
    
    def available(self, obj):
        if obj.pk:
            return obj.available
        return '-'
    available.short_description = 'Available Stock'
    
    def reserved(self, obj):
        if obj.pk:
            return obj.reserved
        return '-'
    reserved.short_description = 'Reserved Stock'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 'product', 'name', 'price', 'final_price_display', 'weight_grams',
        'on_sale', 'stock_status', 'is_active', 'is_featured', 'created'
    )
    list_filter = (
        'product__category', 'on_sale', 'is_active', 'is_featured',
        'discount_type', 'created', 'last_modified'
    )
    search_fields = (
        'sku', 'name', 'product__name', 'product__slug',
        'barcode', 'product__category__name'
    )
    readonly_fields = (
        'created', 'last_modified', 'final_price_display',
        'stock_status', 'image_preview'
    )
    date_hierarchy = 'created'
    inlines = [ProductVariantImageInline, InventoryInline]
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product', 'sku', 'name', 'barcode')
        }),
        ('Pricing', {
            'fields': (
                'price', 'cost_price', 'final_price_display',
                'on_sale', 'discount_type', 'discount_value'
            )
        }),
        ('Product Details', {
            'fields': ('weight_grams', 'attributes'),
            'classes': ('collapse',)
        }),
        ('Availability', {
            'fields': ('available_from', 'available_to')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Stock Information', {
            'fields': ('stock_status',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def final_price_display(self, obj):
        if obj.pk:
            final_price = obj.final_price
            if obj.on_sale and obj.discount_value:
                discount_type = 'Amount' if obj.discount_type == 'amount' else 'Percent'
                return format_html(
                    '<strong>${}</strong><br/><small style="color: #888;">'
                    'Original: ${} | Discount: {} {}</small>',
                    final_price,
                    obj.price,
                    obj.discount_value,
                    discount_type
                )
            return format_html('<strong>${}</strong>', final_price)
        return '-'
    final_price_display.short_description = 'Final Price'
    
    def stock_status(self, obj):
        if hasattr(obj, 'inventory'):
            inv = obj.inventory
            available = inv.available
            quantity = inv.quantity
            reserved = inv.reserved
            
            if available <= 0:
                color = 'red'
                status = 'Out of Stock'
            elif available <= inv.low_stock_threshold:
                color = 'orange'
                status = 'Low Stock'
            else:
                color = 'green'
                status = 'In Stock'
            
            return format_html(
                '<span style="color: {};"><strong>{}</strong></span><br/>'
                '<small>Available: {} | Total: {} | Reserved: {}</small>',
                color, status, available, quantity, reserved
            )
        return format_html('<span style="color: #888;">No inventory record</span>')
    stock_status.short_description = 'Stock Status'
    
    def image_preview(self, obj):
        if obj.pk:
            first_image = obj.images.filter(is_active=True).order_by('ordering', 'id').first()
            if first_image and first_image.image:
                return format_html(
                    '<img src="{}" style="max-width: 100px; max-height: 100px; object-fit: cover;" />',
                    first_image.image.url
                )
        return 'No image'
    image_preview.short_description = 'Variant Image'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'product__category').prefetch_related('images', 'inventory')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Auto-create inventory if it doesn't exist
        if not hasattr(obj, 'inventory'):
            Inventory.objects.create(variant=obj, quantity=0)


@admin.register(ProductVariantImage)
class ProductVariantImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'variant', 'image_preview', 'ordering', 'is_active', 'created')
    list_filter = ('is_active', 'created', 'last_modified')
    search_fields = (
        'variant__sku', 'variant__name', 'variant__product__name',
        'variant__product__slug'
    )
    list_editable = ('ordering', 'is_active')
    readonly_fields = ('created', 'last_modified', 'image_preview')
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Image Information', {
            'fields': ('variant', 'image', 'image_preview', 'ordering', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px; object-fit: cover;" />',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Preview'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('variant', 'variant__product')


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        'variant', 'product_name', 'sku', 'quantity', 'available',
        'reserved', 'low_stock_threshold', 'stock_status',
    )
    list_filter = ('low_stock_threshold',)
    search_fields = (
        'variant__sku', 'variant__name', 'variant__product__name',
        'variant__product__slug'
    )
    readonly_fields = ('variant', 'available', 'reserved', 'stock_status')
    
    fieldsets = (
        ('Variant Information', {
            'fields': ('variant',)
        }),
        ('Stock Information', {
            'fields': ('quantity', 'low_stock_threshold', 'available', 'reserved', 'stock_status')
        }),
    )
    
    def product_name(self, obj):
        return obj.variant.product.name
    product_name.short_description = 'Product'
    
    def sku(self, obj):
        return obj.variant.sku
    sku.short_description = 'SKU'
    
    def stock_status(self, obj):
        available = obj.available
        if available <= 0:
            color = 'red'
            status = 'Out of Stock'
        elif available <= obj.low_stock_threshold:
            color = 'orange'
            status = 'Low Stock'
        else:
            color = 'green'
            status = 'In Stock'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    stock_status.short_description = 'Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('variant', 'variant__product', 'variant__product__category')
    
    def has_add_permission(self, request):
        # Inventory should be created via ProductVariant admin
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion, only allow editing
        return False


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'product', 'user', 'rating', 'is_active', 
        'is_verified_purchase', 'created', 'has_review'
    )
    list_filter = ('rating', 'is_active', 'is_verified_purchase', 'created', 'deleted')
    search_fields = ('product__name', 'user__email', 'user__full_name', 'review')
    readonly_fields = ('created', 'last_modified', 'deleted')
    date_hierarchy = 'created'
    list_per_page = 25
    
    fieldsets = (
        ('Rating Information', {
            'fields': ('product', 'user', 'rating', 'review')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified_purchase', 'deleted')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def has_review(self, obj):
        return bool(obj.review)
    has_review.boolean = True
    has_review.short_description = 'Has Review'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'user')
    
    def get_readonly_fields(self, request, obj=None):
        # Make user and product readonly when editing existing rating
        if obj:
            return self.readonly_fields + ('user', 'product')
        return self.readonly_fields
