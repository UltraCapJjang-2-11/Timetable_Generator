# home/templatetags/org_tags.py
from django import template
from data_manager.models import College, Department, Major

register = template.Library()

"""
Django 템플릿에서 {% org_dropdowns %}과 같이 이 태그를 사용하면, 
데이터베이스에서 가져온 계층적 카테고리 목록이 _org_dropdowns.html 템플릿을 통해 
HTML 드롭다운 메뉴 형태로 렌더링되어 웹 페이지에 삽입
"""

@register.inclusion_tag('home/dropdown/_org_dropdowns.html')
def org_dropdowns():
    """
    단과대학, 학과, 전공을 한 번에 가져와서
    partial template 에 넘겨줍니다.
    """
    colleges = list(
        College.objects
               .all()
               .order_by('college_name')
               .values('college_id', 'college_name')
    )

    departments = list(
        Department.objects
                  .all()
                  .order_by('dept_name')
                  .values('dept_id', 'dept_name', 'college_id')
    )

    majors = list(
        Major.objects
             .all()
             .order_by('major_name')
             .values('major_id', 'major_name', 'dept_id')
    )

    return {
        'colleges':    colleges,
        'departments': departments,
        'majors':      majors,
    }
