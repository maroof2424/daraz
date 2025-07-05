from .models import Category
from .views import get_cart_count, get_wishlist_count

def store_context(request):
    """Add common store data to all templates"""
    context = {
        'cart_count': get_cart_count(request),
        'wishlist_count': get_wishlist_count(request),
    }
    
    # Add categories for navigation
    context['nav_categories'] = Category.objects.filter(
        is_active=True,
        parent=None
    ).prefetch_related('children')[:8]
    
    return context