from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Blog, BlogTag, BlogImage, BlogCategory


class BlogImageInline(admin.TabularInline):
    model = BlogImage
    extra = 3
    fields = ('image', 'image_preview', 'alt_text', 'ordering', 'is_active')
    readonly_fields = ('image_preview',)
    ordering = ('ordering', 'id')

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
        return qs.filter(deleted=False).select_related('blog')


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'blog_count', 'created', 'last_modified')
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

    def blog_count(self, obj):
        count = obj.blogs.filter(deleted=False, status='published').count()
        if count > 0:
            url = reverse('admin:blogs_blog_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    blog_count.short_description = 'Blogs'


@admin.register(BlogTag)
class BlogTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'blog_count', 'created', 'last_modified')
    list_filter = ('is_active', 'created', 'last_modified')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created', 'last_modified')
    date_hierarchy = 'created'

    fieldsets = (
        ('Tag Information', {
            'fields': ('name', 'slug', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )

    def blog_count(self, obj):
        count = obj.blogs.filter(deleted=False, status='published').count()
        if count > 0:
            url = reverse('admin:blogs_blog_changelist') + f'?tags__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    blog_count.short_description = 'Blogs'


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author',
        'category',
        'status',
        'is_active',
        'image_count',
        'view_count',
        'published_at',
        'created',
    )
    list_filter = (
        'status',
        'is_active',
        'category',
        'author',
        'published_at',
        'created',
    )
    search_fields = ('title', 'slug', 'excerpt', 'content', 'author__email', 'category__name')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields = (
        'created',
        'last_modified',
        'view_count',
        'reading_time',
        'images_preview',
    )
    date_hierarchy = 'published_at'
    inlines = [BlogImageInline]

    fieldsets = (
        ('Blog Information', {
            'fields': ('title', 'slug', 'author', 'category', 'tags')
        }),
        ('Content', {
            'fields': ('featured_video', 'excerpt', 'content')
        }),
        ('Images', {
            'fields': ('images_preview',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'published_at')
        }),
        ('Statistics', {
            'fields': ('view_count', 'reading_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'last_modified'),
            'classes': ('collapse',)
        }),
    )

    def image_count(self, obj):
        """Display count of active images"""
        count = obj.images.filter(is_active=True, deleted=False).count()
        if count > 0:
            url = reverse('admin:blogs_blogimage_changelist') + f'?blog__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    image_count.short_description = 'Images'

    def images_preview(self, obj):
        """Display preview of all blog images"""
        if obj.pk:
            images = obj.images.filter(is_active=True, deleted=False).order_by('ordering', 'id')[:5]
            if images:
                html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
                for img in images:
                    if img.image:
                        html += format_html(
                            '<div style="text-align: center;"><img src="{}" style="max-width: 120px; max-height: 120px; object-fit: cover; border: 1px solid #ddd; border-radius: 4px;" /><br/><small>{}</small></div>',
                            img.image.url,
                            img.alt_text or f'Image {img.ordering + 1}'
                        )
                html += '</div>'
                total = obj.images.filter(is_active=True, deleted=False).count()
                if total > 5:
                    html += format_html('<p><small>Showing 5 of {} images. Use the inline editor below to manage all images.</small></p>', total)
                return format_html(html)
        return 'No images. Add images using the inline editor below.'
    images_preview.short_description = 'Images Preview'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(deleted=False).select_related('author', 'category').prefetch_related('tags', 'images')


@admin.register(BlogImage)
class BlogImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'blog', 'image_preview', 'alt_text', 'ordering', 'is_active', 'created')
    list_filter = ('is_active', 'created', 'last_modified')
    search_fields = ('blog__title', 'alt_text')
    list_editable = ('ordering', 'is_active')
    readonly_fields = ('created', 'last_modified', 'image_preview')
    date_hierarchy = 'created'

    fieldsets = (
        ('Image Information', {
            'fields': ('blog', 'image', 'image_preview', 'alt_text', 'ordering', 'is_active')
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
        return qs.filter(deleted=False).select_related('blog')

    def save_model(self, request, obj, form, change):
        """Auto-set author if not set"""
        if not obj.author and request.user.is_authenticated:
            obj.author = request.user
        super().save_model(request, obj, form, change)
