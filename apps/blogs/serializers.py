from rest_framework import serializers
from django.conf import settings
from .models import Blog, BlogTag, BlogImage, BlogCategory


class BlogImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BlogImage
        fields = (
            "id",
            "blog",
            "image",
            "image_url",
            "is_active",
            "alt_text",
            "ordering",
            "created",
            "last_modified",
        )
        read_only_fields = ("id", "created", "last_modified", "image_url")

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return f"{settings.MEDIA_URL}{obj.image}"
        return None


class BlogCategorySerializer(serializers.ModelSerializer):
    blog_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "blog_count",
            "created",
            "last_modified",
        )
        read_only_fields = ("id", "created", "last_modified", "blog_count", "slug")

    def get_blog_count(self, obj):
        """Get count of published blogs in this category"""
        return obj.blogs.filter(
            status='published',
            is_active=True,
            deleted=False
        ).count()


class BlogTagSerializer(serializers.ModelSerializer):
    blog_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogTag
        fields = (
            "id",
            "name",
            "slug",
            "is_active",
            "blog_count",
            "created",
            "last_modified",
        )
        read_only_fields = ("id", "created", "last_modified", "blog_count", "slug")

    def get_blog_count(self, obj):
        """Get count of published blogs with this tag"""
        return obj.blogs.filter(
            status='published',
            is_active=True,
            deleted=False
        ).count()


class BlogSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_email = serializers.SerializerMethodField()
    reading_time = serializers.ReadOnlyField()
    category = BlogCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=BlogCategory.objects.filter(is_active=True, deleted=False),
        write_only=True,
        required=False,
        source='category',
        allow_null=True
    )
    tags = BlogTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=BlogTag.objects.filter(is_active=True, deleted=False),
        write_only=True,
        required=False,
        source='tags'
    )
    images = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = (
            "id",
            "title",
            "slug",
            "author",
            "author_name",
            "author_email",
            "category",
            "category_id",
            "featured_video",
            "tags",
            "tag_ids",
            "images",
            "excerpt",
            "content",
            "status",
            "is_active",
            "published_at",
            "view_count",
            "reading_time",
            "created",
            "last_modified",
        )
        read_only_fields = (
            "id",
            "created",
            "last_modified",
            "author_name",
            "author_email",
            "reading_time",
            "view_count",
            "slug",
        )

    def get_author_name(self, obj):
        return obj.author_name

    def get_author_email(self, obj):
        return obj.author.email if obj.author else None

    def get_images(self, obj):
        """Get active blog images ordered by ordering field"""
        blog_images = obj.images.filter(is_active=True, deleted=False).order_by('ordering', 'id')
        return BlogImageSerializer(blog_images, many=True, context=self.context).data

    def create(self, validated_data):
        """Automatically set author from request if authenticated"""
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['author'] = request.user
        return super().create(validated_data)
