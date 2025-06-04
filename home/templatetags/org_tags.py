# home/templatetags/org_tags.py
from django import template
from data_manager.models import College, Department, Major

register = template.Library()

@register.inclusion_tag('home/_org_dropdowns.html')
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
