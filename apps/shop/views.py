from rest_framework import permissions, filters, generics
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Categories,
    Products,
    ProductImages,
    ProductVariant,
    ProductVariantImage,
    Inventory,
)
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    ProductVariantSerializer,
    ProductVariantImageSerializer,
    InventorySerializer,
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
    lookup_field = "slug"

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
