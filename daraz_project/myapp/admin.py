from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import *

# Custom User Admin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone", "date_of_birth", "profile_image")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (_("Extra info"), {"fields": ("user_type", "is_verified")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "user_type", "phone", "date_of_birth"),
        }),
    )
    list_display = ("username", "email", "user_type", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

# Register other models
admin.site.register(Address)
admin.site.register(Category)
admin.site.register(Brand)

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("business_name", "user", "is_approved", "is_active", "rating", "total_sales")
    search_fields = ("business_name", "business_email", "business_phone")
    list_filter = ("is_approved", "is_active")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "category", "price", "stock_quantity", "status", "is_featured")
    search_fields = ("name", "sku")
    list_filter = ("status", "category", "vendor", "brand", "is_featured")

admin.site.register(ProductImage)
admin.site.register(ProductAttribute)
admin.site.register(ProductAttributeValue)
admin.site.register(ProductVariation)
admin.site.register(Cart)
admin.site.register(CartItem)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "status", "payment_status", "total_amount", "created_at")
    search_fields = ("order_id", "user__username", "user__email")
    list_filter = ("status", "payment_status", "created_at")

admin.site.register(OrderItem)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "rating", "is_verified_purchase", "is_approved", "created_at")
    search_fields = ("user__username", "product__name", "title")
    list_filter = ("is_verified_purchase", "is_approved")

admin.site.register(Wishlist)
admin.site.register(Coupon)
