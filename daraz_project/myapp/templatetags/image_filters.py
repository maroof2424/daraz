# myapp/templatetags/image_filters.py

from django import template

register = template.Library()

@register.filter
def get_main_image(images):
    return images.filter(is_primary=True).first()
