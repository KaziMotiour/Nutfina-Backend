from django_filters import FilterSet, CharFilter
from .models import Products

class ProductFilter(FilterSet):    
    category = CharFilter(method='filter_category')
    
    search = CharFilter(method='filter_search')
    class Meta:
        model = Products
        fields = {
            'is_active': ['exact'],
            'is_featured': ['exact'],
            'name': ['icontains'],
            
        }

    def filter_category(self, queryset, name, value):
        return queryset.filter(category__slug=value)
    
    def filter_search(self, queryset, name, value):
        print(value)
        print(queryset.filter(name__icontains=value).count())
        return queryset.filter(name__icontains=value)