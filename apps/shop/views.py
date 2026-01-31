from rest_framework import permissions, filters, generics
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .models import (
    Categories,
    Products,
    ProductImages,
    ProductVariant,
    ProductVariantImage,
    Inventory,
    ProductRating,
)
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    ProductVariantSerializer,
    ProductVariantImageSerializer,
    InventorySerializer,
    ProductRatingSerializer,
)
from .filters import ProductFilter  


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Categories.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categories.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "slug"

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Products.objects.all().prefetch_related('productimages_set', 'productvariant_set')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.prefetch_related('productimages_set', 'productvariant_set',)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "pk"

class FeaturedProductListView(generics.ListAPIView):
    """
    Dedicated view for featured products.
    Returns only active products marked as featured, optimized for Deal component.
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Public endpoint
    
    def get_queryset(self):
        """
        Return only featured and active products with optimized prefetching.
        """
        queryset = Products.objects.filter(
            is_featured=True,
            is_active=True
        ).prefetch_related(
            'productimages_set',
            'productvariant_set',
            'productvariant_set__images',
            'productvariant_set__product__productimages_set'
        ).select_related('category')
        
        # Order by creation date (newest first) or any other preferred ordering
        return queryset.order_by('-created', '-id')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class ProductImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductImages.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "is_active"]
    ordering_fields = ["ordering", "created_at", "updated_at"]
    ordering = ["ordering", "id"]

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImages.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductVariantListCreateView(generics.ListCreateAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["product", "is_active", "is_featured", "on_sale", "discount_type"]
    search_fields = ["sku", "name", "barcode"]
    ordering_fields = ["created_at", "updated_at", "price", "sku"]
    ordering = ["-created_at"]

class ProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductVariantImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductVariantImage.objects.all()
    serializer_class = ProductVariantImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["variant", "is_active"]
    ordering_fields = ["ordering", "created_at", "updated_at"]
    ordering = ["ordering", "id"]

class ProductVariantImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductVariantImage.objects.all()
    serializer_class = ProductVariantImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class InventoryListCreateView(generics.ListCreateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["variant"]
    ordering_fields = ["created_at", "updated_at", "quantity"]
    ordering = ["-created_at"]

class InventoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductRatingListCreateView(generics.ListCreateAPIView):
    queryset = ProductRating.objects.filter(deleted=False, is_active=True)
    serializer_class = ProductRatingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "user", "rating", "is_active", "is_verified_purchase"]
    ordering_fields = ["created", "rating"]
    ordering = ["-created"]
    
    def get_queryset(self):
        queryset = ProductRating.objects.filter(deleted=False)
        # If user is authenticated, show their own inactive ratings too
        if self.request.user and self.request.user.is_authenticated:
            queryset = ProductRating.objects.filter(
                deleted=False
            ).filter(
                models.Q(is_active=True) | models.Q(user=self.request.user)
            )
        else:
            queryset = queryset.filter(is_active=True)
        return queryset.select_related('product', 'user')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductRatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductRating.objects.filter(deleted=False)
    serializer_class = ProductRatingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = ProductRating.objects.filter(deleted=False)
        # If user is authenticated, allow them to see/edit their own ratings
        if self.request.user and self.request.user.is_authenticated:
            return queryset.select_related('product', 'user')
        # For anonymous users, only show active ratings
        return queryset.filter(is_active=True).select_related('product', 'user')
    
    def perform_update(self, serializer):
        # Only allow users to update their own ratings
        instance = self.get_object()
        if self.request.user and self.request.user.is_authenticated:
            if instance.user != self.request.user and not self.request.user.is_staff:
                raise PermissionDenied("You can only update your own ratings.")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Soft delete by setting deleted=True instead of actually deleting
        instance.deleted = True
        instance.is_active = False
        instance.save()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
