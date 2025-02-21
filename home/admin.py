from django.contrib import admin
from .models import Student, Professor, Course, ClassTime, StudentGoal

admin.site.register(Student)
admin.site.register(Professor)
admin.site.register(Course)
admin.site.register(ClassTime)
admin.site.register(StudentGoal)
