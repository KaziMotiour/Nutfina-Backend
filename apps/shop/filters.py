from django_filters import FilterSet, CharFilter
from .models import Products

class ProductFilter(FilterSet):    
    category = CharFilter(method='filter_category')
    
    class Meta:
        model = Products
        fields = {
            'is_active': ['exact'],
            'is_featured': ['exact'],
        }

    def filter_category(self, queryset, name, value):
        return queryset.filter(category__slug=value)