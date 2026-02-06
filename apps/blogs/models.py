from django.db import models
from django.utils.text import slugify
from apps.core.models import BaseModel
from apps.user.models import User


class BlogCategory(BaseModel):
    """Blog category model"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Description of the category")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Blog Category'
        verbose_name_plural = 'Blog Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogTag(BaseModel):
    """Blog tag model"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Blog Tag'
        verbose_name_plural = 'Blog Tags'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Blog(BaseModel):
    """Blog post model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly version of the title")
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_posts'
    )
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blogs',
        help_text="Category for the blog post"
    )
    featured_video = models.URLField(
        blank=True,
        null=True,
        help_text="Featured video URL for the blog post"
    )
    tags = models.ManyToManyField(
        BlogTag,
        blank=True,
        related_name='blogs',
        help_text="Tags for the blog post"
    )
    excerpt = models.TextField(
        max_length=500,
        blank=True,
        help_text="Short summary or excerpt of the blog post"
    )
    content = models.TextField(help_text="Full content of the blog post")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Publication date and time"
    )
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['is_active']),
            models.Index(fields=['published_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
        ]
        ordering = ['-published_at', '-created']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            # Ensure slug uniqueness
            while Blog.objects.filter(slug=slug, deleted=False).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Auto-set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def author_name(self):
        """Get author's full name or email"""
        if self.author:
            return self.author.full_name or self.author.email
        return "Admin"

    @property
    def reading_time(self):
        """Estimate reading time in minutes (assuming 200 words per minute)"""
        word_count = len(self.content.split())
        return max(1, round(word_count / 200))


class BlogImage(BaseModel):
    """Blog image model for multiple images per blog post"""
    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='blogs/images/',
        blank=True,
        null=True,
        help_text="Image for the blog post"
    )
    is_active = models.BooleanField(default=True)
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Alternative text for the image"
    )
    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Order in which images should be displayed"
    )

    class Meta:
        ordering = ['ordering', 'id']
        verbose_name = 'Blog Image'
        verbose_name_plural = 'Blog Images'

    def __str__(self):
        return f"{self.blog.title} - Image {self.ordering + 1}"
