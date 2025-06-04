# home/services.py
from data_manager.models import College, Department, Major

class OrganizationService:
    def get_colleges(self):
        return College.objects.all().order_by('college_name')

    def get_departments(self, college_id):
        return Department.objects.filter(college_id=college_id).order_by('dept_name')

    def get_majors(self, dept_id):
        return Major.objects.filter(dept_id=dept_id).order_by('major_name')
