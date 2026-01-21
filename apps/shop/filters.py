from django_filters import FilterSet
from .models import Products

class ProductFilter(FilterSet):
    class Meta:
        model = Products
        fields = {
            'category': ['exact'],
            'is_active': ['exact'],
            'is_featured': ['exact'],
        }