
"""
Django 템플릿에서 {% category_dropdown %}과 같이 이 태그를 사용하면,
데이터베이스에서 가져온 계층적 카테고리 목록이 _category_dropdown.html 템플릿을 통해
HTML 드롭다운 메뉴 형태로 렌더링되어 웹 페이지에 삽입
"""
from django import template
from data_manager.models import Category

register = template.Library()

@register.inclusion_tag('home/dropdown/_category_dropdown.html')
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
