# home/templatetags/category_tags.py
from django import template
from data_manager.models import Category

register = template.Library()

@register.inclusion_tag('home/_category_dropdown.html')
def category_dropdown():
    """
    계층적 카테고리를 모두 가져와서
    partial template 에 넘겨줍니다.
    """
    cats = list(
        Category.objects
                .all()
                .order_by('category_level', 'category_name')
                .values('category_id', 'category_name', 'parent_category_id', 'category_level')
    )
    return {'categories': cats}
