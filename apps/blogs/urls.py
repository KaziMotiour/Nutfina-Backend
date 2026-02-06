from django.urls import path
from .views import (
    BlogListCreateView,
    BlogCreateView,
    BlogDetailView,
    FeaturedBlogListView,
    BlogCategoryListCreateView,
    BlogCategoryDetailView,
    BlogTagListCreateView,
    BlogTagDetailView,
    BlogImageListCreateView,
    BlogImageDetailView,
)

urlpatterns = [
    # Blog Posts
    path('posts/', BlogListCreateView.as_view(), name='blog-list-create'),
    path('posts/create/', BlogCreateView.as_view(), name='blog-create'),
    path('posts/featured/', FeaturedBlogListView.as_view(), name='blog-featured-list'),
    path('posts/<slug:slug>/', BlogDetailView.as_view(), name='blog-detail'),

    # Blog Categories
    path('categories/', BlogCategoryListCreateView.as_view(), name='blog-category-list-create'),
    path('categories/<slug:slug>/', BlogCategoryDetailView.as_view(), name='blog-category-detail'),

    # Blog Tags
    path('tags/', BlogTagListCreateView.as_view(), name='blog-tag-list-create'),
    path('tags/<slug:slug>/', BlogTagDetailView.as_view(), name='blog-tag-detail'),

    # Blog Images
    path('images/', BlogImageListCreateView.as_view(), name='blog-image-list-create'),
    path('images/<int:pk>/', BlogImageDetailView.as_view(), name='blog-image-detail'),
]
