# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.db import transaction
from .models import *
from .forms import *
import json

# Add this import at the top of your views.py file
from django.utils import timezone




def home(request):
    """Homepage with featured products and categories"""
    featured_products = Product.objects.filter(
        status='active', 
        is_featured=True
    ).select_related('vendor', 'category')[:12]
    
    categories = Category.objects.filter(
        is_active=True, 
        parent=None
    ).order_by('sort_order')[:8]
    
    # Best selling products
    best_selling = Product.objects.filter(
        status='active'
    ).annotate(
        total_sold=Count('orderitem')
    ).order_by('-total_sold')[:8]
    
    # New arrivals
    new_arrivals = Product.objects.filter(
        status='active'
    ).order_by('-created_at')[:8]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'best_selling': best_selling,
        'new_arrivals': new_arrivals,
    }
    return render(request, 'store/home.html', context)

class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'
    paginate_by = 24
    context_object_name = 'products'

    def get_queryset(self):
        queryset = Product.objects.filter(status='active').select_related(
            'vendor', 'category', 'brand'
        ).prefetch_related('images')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        
        # Brand filter
        brand_slug = self.request.GET.get('brand')
        if brand_slug:
            brand = get_object_or_404(Brand, slug=brand_slug)
            queryset = queryset.filter(brand=brand)
        
        # Price range filter
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-rating')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('name')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['brands'] = Brand.objects.filter(is_active=True)
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Product.objects.filter(status='active').select_related(
            'vendor', 'category', 'brand'
        ).prefetch_related('images', 'variations', 'reviews__user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Reviews
        reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
        context['reviews'] = reviews
        
        # Related products
        related_products = Product.objects.filter(
            category=product.category,
            status='active'
        ).exclude(id=product.id)[:8]
        context['related_products'] = related_products
        
        # Check if in wishlist
        if self.request.user.is_authenticated:
            context['in_wishlist'] = Wishlist.objects.filter(
                user=self.request.user,
                product=product
            ).exists()
        
        return context

@login_required
def add_to_cart(request):
    """Add product to cart via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        variation_id = data.get('variation_id')
        quantity = int(data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id, status='active')
        variation = None
        
        if variation_id:
            variation = get_object_or_404(ProductVariation, id=variation_id)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'session_key': request.session.session_key}
        )
        
        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variation=variation,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Get cart count
        cart_count = CartItem.objects.filter(cart=cart).count()
        
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart successfully!',
            'cart_count': cart_count
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def cart_view(request):
    """Display cart items"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related(
            'product', 'variation'
        )
    except Cart.DoesNotExist:
        cart_items = []
    
    # Calculate totals
    subtotal = sum(item.total_price for item in cart_items)
    shipping_cost = 150 if subtotal < 2000 else 0  # Free shipping above 2000
    total = subtotal + shipping_cost
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    }
    return render(request, 'store/cart.html', context)

@login_required
def update_cart_item(request):
    """Update cart item quantity via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity'))
        
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
            
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item.delete()
            
            return JsonResponse({'success': True})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Item not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def delete_cart_item(request, item_id):
    """Delete a cart item"""
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
        cart_item.delete()
        messages.success(request, "Item removed from cart.")
    except CartItem.DoesNotExist:
        messages.error(request, "Cart item not found.")
    
    return redirect('cart') 
@login_required
def checkout(request):
    """Checkout process"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related(
            'product', 'variation'
        )
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')
    
    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')
    
    # Get user addresses
    addresses = Address.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order
            with transaction.atomic():
                # Calculate totals
                subtotal = sum(item.total_price for item in cart_items)
                shipping_cost = 150 if subtotal < 2000 else 0
                tax_amount = 0  # Add tax calculation if needed
                total_amount = subtotal + shipping_cost + tax_amount
                
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    shipping_full_name=form.cleaned_data['full_name'],
                    shipping_phone=form.cleaned_data['phone'],
                    shipping_address_line_1=form.cleaned_data['address_line_1'],
                    shipping_address_line_2=form.cleaned_data['address_line_2'],
                    shipping_city=form.cleaned_data['city'],
                    shipping_state=form.cleaned_data['state'],
                    shipping_postal_code=form.cleaned_data['postal_code'],
                    shipping_country=form.cleaned_data['country'],
                    subtotal=subtotal,
                    shipping_cost=shipping_cost,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    payment_method=form.cleaned_data['payment_method'],
                    notes=form.cleaned_data.get('notes', ''),
                )
                
                # Create order items
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        variation=cart_item.variation,
                        vendor=cart_item.product.vendor,
                        product_name=cart_item.product.name,
                        product_price=cart_item.variation.price if cart_item.variation and cart_item.variation.price else cart_item.product.price,
                        quantity=cart_item.quantity,
                        total_price=cart_item.total_price,
                    )
                
                # Clear cart
                cart_items.delete()
                
                messages.success(request, f'Order {order.order_id} placed successfully!')
                return redirect('order_confirmation', order_id=order.order_id)
    else:
        form = CheckoutForm()
    
    # Calculate totals
    subtotal = sum(item.total_price for item in cart_items)
    shipping_cost = 150 if subtotal < 2000 else 0
    total = subtotal + shipping_cost
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'addresses': addresses,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    }
    return render(request, 'store/checkout.html', context)

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'store/order_confirmation.html', {'order': order})

@login_required
def order_history(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    return render(request, 'store/order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})

@login_required
def wishlist(request):
    """User's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        'product'
    ).order_by('-created_at')
    
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def toggle_wishlist(request):
    """Add/remove product from wishlist via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        product = get_object_or_404(Product, id=product_id)
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            wishlist_item.delete()
            in_wishlist = False
        else:
            in_wishlist = True
        
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'message': 'Added to wishlist!' if in_wishlist else 'Removed from wishlist!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def add_review(request, product_id):
    """Add product review"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user has purchased this product
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__status='delivered'
    ).exists()
    
    # Check if user already reviewed this product
    existing_review = Review.objects.filter(
        user=request.user,
        product=product
    ).first()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            if existing_review:
                # Update existing review
                existing_review.rating = form.cleaned_data['rating']
                existing_review.title = form.cleaned_data['title']
                existing_review.comment = form.cleaned_data['comment']
                existing_review.save()
                messages.success(request, 'Review updated successfully!')
            else:
                # Create new review
                review = form.save(commit=False)
                review.user = request.user
                review.product = product
                review.is_verified_purchase = has_purchased
                review.save()
                
                # Update product rating
                avg_rating = Review.objects.filter(
                    product=product,
                    is_approved=True
                ).aggregate(Avg('rating'))['rating__avg']
                
                product.rating = round(avg_rating, 2) if avg_rating else 0
                product.review_count = Review.objects.filter(
                    product=product,
                    is_approved=True
                ).count()
                product.save()
                
                messages.success(request, 'Review added successfully!')
            
            return redirect('product_detail', slug=product.slug)
    else:
        form = ReviewForm(instance=existing_review)
    
    context = {
        'form': form,
        'product': product,
        'has_purchased': has_purchased,
        'existing_review': existing_review,
    }
    return render(request, 'store/add_review.html', context)

# Vendor Views
@login_required
def vendor_dashboard(request):
    """Vendor dashboard"""
    if request.user.user_type != 'vendor':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, 'Vendor profile not found.')
        return redirect('home')
    
    # Dashboard statistics
    total_products = vendor.products.filter(status='active').count()
    total_orders = OrderItem.objects.filter(vendor=vendor).count()
    pending_orders = OrderItem.objects.filter(
        vendor=vendor,
        order__status__in=['pending', 'confirmed']
    ).count()
    
    recent_orders = OrderItem.objects.filter(
        vendor=vendor
    ).select_related('order', 'product').order_by('-order__created_at')[:10]
    
    context = {
        'vendor': vendor,
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
    }
    return render(request, 'vendor/dashboard.html', context)

@login_required
def vendor_products(request):
    """Vendor product management"""
    if request.user.user_type != 'vendor':
        return redirect('home')
    
    vendor = request.user.vendor
    products = vendor.products.all().order_by('-created_at')
    
    paginator = Paginator(products, 20)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    return render(request, 'vendor/products.html', {'products': products})

@login_required
def vendor_add_product(request):
    """Add new product"""
    if request.user.user_type != 'vendor':
        return redirect('home')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = request.user.vendor
            product.save()
            
            messages.success(request, 'Product added successfully!')
            return redirect('vendor_products')
    else:
        form = ProductForm()
    
    return render(request, 'vendor/add_product.html', {'form': form})

@login_required
def vendor_edit_product(request, product_id):
    """Edit product"""
    if request.user.user_type != 'vendor':
        return redirect('home')
    
    product = get_object_or_404(Product, id=product_id, vendor=request.user.vendor)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('vendor_products')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'vendor/edit_product.html', {
        'form': form,
        'product': product
    })

@login_required
def vendor_orders(request):
    """Vendor orders"""
    if request.user.user_type != 'vendor':
        return redirect('home')
    
    vendor = request.user.vendor
    order_items = OrderItem.objects.filter(
        vendor=vendor
    ).select_related('order', 'product').order_by('-order__created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        order_items = order_items.filter(order__status=status_filter)
    
    paginator = Paginator(order_items, 20)
    page = request.GET.get('page')
    order_items = paginator.get_page(page)
    
    context = {
        'order_items': order_items,
        'status_filter': status_filter,
    }
    return render(request, 'vendor/orders.html', context)

@login_required
def update_order_status(request):
    """Update order status via AJAX"""
    if request.method == 'POST' and request.user.user_type == 'vendor':
        data = json.loads(request.body)
        order_id = data.get('order_id')
        status = data.get('status')
        
        try:
            order = Order.objects.get(id=order_id)
            # Check if vendor has items in this order
            if OrderItem.objects.filter(order=order, vendor=request.user.vendor).exists():
                order.status = status
                order.save()
                return JsonResponse({'success': True})
        except Order.DoesNotExist:
            pass
    
    return JsonResponse({'success': False})

# AJAX Views for dynamic functionality
def get_subcategories(request):
    """Get subcategories via AJAX"""
    parent_id = request.GET.get('parent_id')
    subcategories = Category.objects.filter(
        parent_id=parent_id,
        is_active=True
    ).values('id', 'name')
    
    return JsonResponse(list(subcategories), safe=False)

def search_suggestions(request):
    """Product search suggestions via AJAX"""
    query = request.GET.get('q', '')
    if len(query) >= 2:
        products = Product.objects.filter(
            name__icontains=query,
            status='active'
        ).values('name', 'slug')[:10]
        
        return JsonResponse(list(products), safe=False)
    
    return JsonResponse([], safe=False)

def apply_coupon(request):
    """Apply coupon code via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code')
        cart_total = float(data.get('cart_total', 0))
        
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
            
            # Check usage limit
            if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
                return JsonResponse({
                    'success': False,
                    'message': 'Coupon usage limit exceeded.'
                })
            
            # Check minimum amount
            if cart_total < coupon.minimum_amount:
                return JsonResponse({
                    'success': False,
                    'message': f'Minimum order amount is ${coupon.minimum_amount}'
                })
            
            # Calculate discount
            if coupon.coupon_type == 'percentage':
                discount = (cart_total * coupon.value) / 100
                if coupon.maximum_discount:
                    discount = min(discount, coupon.maximum_discount)
            else:
                discount = coupon.value
            
            discount = min(discount, cart_total)
            
            return JsonResponse({
                'success': True,
                'discount_amount': discount,
                'message': f'Coupon applied! You saved ${discount:.2f}'
            })
            
        except Coupon.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid coupon code.'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})