from rest_framework import serializers
from django.conf import settings
from .models import (
    Categories,
    Products,
    ProductImages,
    ProductVariant,
    ProductVariantImage,
    Inventory,
    ProductRating,
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
    category_slug = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Products
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "excerpt",
            "description",
            "base_price",
            "is_active",
            "is_featured",
            "images",
            "variants",
            "category_name",
            "category_slug",
            "average_rating",
            "rating_count",
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
    
    def get_average_rating(self, obj):
        """Calculate average rating for the product"""
        from django.db.models import Avg
        result = obj.ratings.filter(is_active=True, deleted=False).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating']
        return round(float(result), 2) if result else 0.0
    
    def get_rating_count(self, obj):
        """Get total count of active ratings"""
        return obj.ratings.filter(is_active=True, deleted=False).count()
    
    def get_category_slug(self, obj):
        return obj.category.slug


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


class ProductRatingSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductRating
        fields = (
            "id",
            "product",
            "product_name",
            "user",
            "user_email",
            "user_name",
            "rating",
            "review",
            "is_active",
            "is_verified_purchase",
            "created",
            "last_modified",
        )
        read_only_fields = ("id", "created", "last_modified", "user_email", "user_name", "product_name")
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None
    
    def get_user_name(self, obj):
        return obj.user.full_name if obj.user and obj.user.full_name else None
    
    def get_product_name(self, obj):
        return obj.product.name if obj.product else None
    
    def create(self, validated_data):
        # Automatically set user from request if authenticated
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)
    
    def validate_rating(self, value):
        """Ensure rating is between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

