from rest_framework import permissions, filters, generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Blog, BlogTag, BlogImage, BlogCategory
from .serializers import BlogSerializer, BlogTagSerializer, BlogImageSerializer, BlogCategorySerializer


class BlogListCreateView(generics.ListCreateAPIView):
    """List and create blog posts"""
    serializer_class = BlogSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tags__id", "category", "status", "is_active"]
    search_fields = ["title", "excerpt", "content"]
    ordering_fields = ["created", "published_at", "view_count", "title"]
    ordering = ["-published_at", "-created"]

    def get_queryset(self):
        """Filter queryset - show published blogs to all, drafts to authors/staff"""
        queryset = Blog.objects.filter(deleted=False).select_related('author', 'category').prefetch_related('tags', 'images')

        # For anonymous users, only show published and active blogs
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(status='published', is_active=True)
        # For authenticated users, show their own drafts and all published blogs
        elif not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status='published', is_active=True) |
                Q(author=self.request.user)
            )
        # Staff users can see all blogs

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class BlogCreateView(generics.CreateAPIView):
    """Create a new blog post with tags"""
    serializer_class = BlogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """Automatically set author to current user and handle tags"""
        # The serializer's create method will handle author assignment
        # Tags are handled via tag_ids field in the serializer
        blog = serializer.save(author=self.request.user)
        return blog


class BlogDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete blog post"""
    queryset = Blog.objects.filter(deleted=False)
    serializer_class = BlogSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = Blog.objects.filter(deleted=False).select_related('author', 'category').prefetch_related('tags', 'images')

        # For anonymous users, only show published and active blogs
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(status='published', is_active=True)
        # For authenticated users, show their own drafts and all published blogs
        elif not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status='published', is_active=True) |
                Q(author=self.request.user)
            )
        # Staff users can see all blogs

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Increment view count when blog is viewed"""
        instance = self.get_object()
        
        # Only increment for published blogs
        if instance.status == 'published' and instance.is_active:
            instance.view_count += 1
            instance.save(update_fields=['view_count'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Only allow author or staff to update"""
        instance = self.get_object()
        if not self.request.user.is_staff and instance.author != self.request.user:
            raise PermissionDenied("You can only update your own blog posts.")
        serializer.save()

    def perform_destroy(self, instance):
        """Only allow author or staff to delete, soft delete"""
        if not self.request.user.is_staff and instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own blog posts.")
        instance.deleted = True
        instance.is_active = False
        instance.save()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class FeaturedBlogListView(generics.ListAPIView):
    """List featured blog posts"""
    serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Return only featured, published, and active blogs"""
        return Blog.objects.filter(
            status='published',
            is_active=True,
            deleted=False
        ).select_related('author', 'category').prefetch_related('tags', 'images').order_by('-published_at', '-created')


class BlogCategoryListCreateView(generics.ListCreateAPIView):
    """List and create blog categories"""
    queryset = BlogCategory.objects.filter(deleted=False, is_active=True)
    serializer_class = BlogCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]
    ordering_fields = ["created", "name"]
    ordering = ["name"]

    def get_queryset(self):
        """Show all categories to authenticated users, only active to anonymous"""
        queryset = BlogCategory.objects.filter(deleted=False)
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        return queryset


class BlogCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete blog category"""
    queryset = BlogCategory.objects.filter(deleted=False)
    serializer_class = BlogCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "slug"

    def perform_destroy(self, instance):
        """Soft delete"""
        instance.deleted = True
        instance.is_active = False
        instance.save()

    def get_queryset(self):
        """Show active categories to all, all categories to authenticated users"""
        queryset = BlogCategory.objects.filter(deleted=False)
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        return queryset


class BlogTagListCreateView(generics.ListCreateAPIView):
    """List and create blog tags"""
    queryset = BlogTag.objects.filter(deleted=False, is_active=True)
    serializer_class = BlogTagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]
    ordering_fields = ["created", "name"]
    ordering = ["name"]

    def get_queryset(self):
        """Show all tags to authenticated users, only active to anonymous"""
        queryset = BlogTag.objects.filter(deleted=False)
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        return queryset


class BlogTagDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete blog tag"""
    queryset = BlogTag.objects.filter(deleted=False)
    serializer_class = BlogTagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "slug"

    def perform_destroy(self, instance):
        """Soft delete"""
        instance.deleted = True
        instance.is_active = False
        instance.save()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class BlogImageListCreateView(generics.ListCreateAPIView):
    """List and create blog images"""
    serializer_class = BlogImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["blog", "is_active"]
    ordering_fields = ["ordering", "created"]
    ordering = ["ordering", "id"]

    def get_queryset(self):
        """Show active images to all, all images to authenticated users"""
        queryset = BlogImage.objects.filter(deleted=False)
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        return queryset.select_related('blog')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class BlogImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete blog image"""
    queryset = BlogImage.objects.filter(deleted=False)
    serializer_class = BlogImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Show active images to all, all images to authenticated users"""
        queryset = BlogImage.objects.filter(deleted=False)
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        return queryset.select_related('blog')

    def perform_destroy(self, instance):
        """Soft delete"""
        instance.deleted = True
        instance.is_active = False
        instance.save()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
