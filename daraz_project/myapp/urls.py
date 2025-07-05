# myapp/urls.py
from django.urls import path, include
from django.contrib.auth import views as django_auth_views
from . import views
from . import auth_views

urlpatterns = [
    # Main store URLs
    path('', views.home, name='home'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Cart and Checkout
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<str:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # User Account
    path('account/orders/', views.order_history, name='order_history'),
    path('account/order/<str:order_id>/', views.order_detail, name='order_detail'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('toggle-wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
    
    # Reviews
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
    
    # Vendor URLs
    path('vendor/', include([
        path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
        path('products/', views.vendor_products, name='vendor_products'),
        path('products/add/', views.vendor_add_product, name='vendor_add_product'),
        path('cart/delete/<int:item_id>/', views.delete_cart_item, name='delete_cart_item'),
        path('products/<int:product_id>/edit/', views.vendor_edit_product, name='vendor_edit_product'),
        path('orders/', views.vendor_orders, name='vendor_orders'),
        path('update-order-status/', views.update_order_status, name='update_order_status'),
    ])),
    
    # AJAX URLs
    path('ajax/subcategories/', views.get_subcategories, name='get_subcategories'),
    path('ajax/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('ajax/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    
    # Authentication URLs
    path('register/', auth_views.register_view, name='register'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    
    # Profile URLs
    path('profile/', auth_views.profile_view, name='profile'),
    path('profile/edit/', auth_views.edit_profile, name='edit_profile'),
    
    # Additional useful URLs
    # Password Change & Reset
path('password-change/', django_auth_views.PasswordChangeView.as_view(
    template_name='auth/password_change.html',
    success_url='/profile/'
), name='password_change'),

path('password-reset/', django_auth_views.PasswordResetView.as_view(
    template_name='auth/password_reset.html',
    email_template_name='auth/password_reset_email.html',
    success_url='/password-reset/done/'
), name='password_reset'),

path('password-reset/done/', django_auth_views.PasswordResetDoneView.as_view(
    template_name='auth/password_reset_done.html'
), name='password_reset_done'),

path('password-reset/<uidb64>/<token>/', django_auth_views.PasswordResetConfirmView.as_view(
    template_name='auth/password_reset_confirm.html',
    success_url='/password-reset/complete/'
), name='password_reset_confirm'),

path('password-reset/complete/', django_auth_views.PasswordResetCompleteView.as_view(
    template_name='auth/password_reset_complete.html'
), name='password_reset_complete'),

]