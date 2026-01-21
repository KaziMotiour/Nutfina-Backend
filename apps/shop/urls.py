from django.urls import path
from .views import (
    CategoryListCreateView,
    CategoryDetailView,
    ProductListCreateView,
    ProductDetailView,
    ProductImageListCreateView,
    ProductImageDetailView,
    ProductVariantListCreateView,
    ProductVariantDetailView,
    ProductVariantImageListCreateView,
    ProductVariantImageDetailView,
    InventoryListCreateView,
    InventoryDetailView,
)

urlpatterns = [
    # Categories
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),

    # Products
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),

    # Product Images
    path('product-images/', ProductImageListCreateView.as_view(), name='product-image-list-create'),
    path('product-images/<int:pk>/', ProductImageDetailView.as_view(), name='product-image-detail'),

    # Variants
    path('variants/', ProductVariantListCreateView.as_view(), name='variant-list-create'),
    path('variants/<int:pk>/', ProductVariantDetailView.as_view(), name='variant-detail'),

    # Variant Images
    path('variant-images/', ProductVariantImageListCreateView.as_view(), name='variant-image-list-create'),
    path('variant-images/<int:pk>/', ProductVariantImageDetailView.as_view(), name='variant-image-detail'),

    # Inventory
    path('inventory/', InventoryListCreateView.as_view(), name='inventory-list-create'),
    path('inventory/<int:pk>/', InventoryDetailView.as_view(), name='inventory-detail'),
]

