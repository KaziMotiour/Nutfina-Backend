from rest_framework import serializers
from django.conf import settings
from .models import (
    Categories,
    Products,
    ProductImages,
    ProductVariant,
    ProductVariantImage,
    Inventory,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ("id", "name", "slug", "description", "is_active", "created", "last_modified")
        read_only_fields = ("id", "created", "last_modified")


class ProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Products
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "description",
            "base_price",
            "is_active",
            "is_featured",
            "images",
            "variants",
            "category_name",
            "created",
            "last_modified",
        )
        read_only_fields = ("id", "created", "last_modified")
    
    def get_images(self, obj):
        """Get active product images"""
        product_images = obj.productimages_set.filter(is_active=True).order_by('ordering', 'id')
        return ProductImageSerializer(product_images, many=True, context=self.context).data
    
    def get_variants(self, obj):
        """Get active variants for the product, prioritizing featured ones"""
        variants = obj.productvariant_set.filter(is_active=True).order_by('-is_featured', 'price')
        return ProductVariantSerializer(variants, many=True, context=self.context).data
    
    def get_category_name(self, obj):
        return obj.category.name


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImages
        fields = (
            "id",
            "product",
            "image",
            "is_active",
            "alt_text",
            "ordering",
            "created",
            "last_modified",
        )
        read_only_fields = ("id", "created", "last_modified")
    
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            # Fallback if no request context
            return f"{settings.MEDIA_URL}{obj.image}"
        return None


class ProductVariantImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariantImage
        fields = ("id", "variant", "image", "is_active", "ordering", "created", "last_modified")
        read_only_fields = ("id", "created", "last_modified")
    
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            # Fallback if no request context
            return f"{settings.MEDIA_URL}{obj.image}"
        return None


class ProductVariantSerializer(serializers.ModelSerializer):
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    images = serializers.SerializerMethodField()
    product_images = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product",
            "sku",
            "name",
            "price",
            "cost_price",
            "weight_grams",
            "barcode",
            "on_sale",
            "discount_type",
            "discount_value",
            "available_from",
            "available_to",
            "attributes",
            "is_featured",
            "is_active",
            "final_price",
            "images",
            "product_images",
            "created",
            "last_modified",
        )
        read_only_fields = ("id", "final_price", "created", "last_modified")
    
    def get_images(self, obj):
        """Get variant images"""
        try:
            # Access images - Django will use prefetched data if available
            # When prefetched, obj.images.all() returns the prefetched queryset
            # When not prefetched, it queries the database
            variant_images = obj.images.filter(is_active=True).order_by('ordering', 'id')
            return ProductVariantImageSerializer(variant_images, many=True, context=self.context).data
        except Exception as e:
            # Fallback: return empty list if anything fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting variant images for variant {obj.id}: {str(e)}")
            return []
    
    def get_product_images(self, obj):
        """Get product images as fallback if variant has no images"""
        if obj.product:
            # Use prefetched product images if available
            if hasattr(obj.product, 'productimages_set'):
                product_images = obj.product.productimages_set.filter(is_active=True).order_by('ordering', 'id')
            else:
                product_images = obj.product.productimages_set.filter(is_active=True).order_by('ordering', 'id')
            return ProductImageSerializer(product_images, many=True, context=self.context).data
        return []


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ("id", "variant", "quantity", "low_stock_threshold", "created", "last_modified")
        read_only_fields = ("id", "created", "last_modified")

