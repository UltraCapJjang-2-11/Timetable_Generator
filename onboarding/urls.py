
from django.urls import path
from .views import *

urlpatterns = [
    path('', onboarding, name='onboarding'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('process-pdf/', ProcessPdfView.as_view(), name='process_pdf'),
    path('save-academic-info/', SaveAcademicInfoView.as_view(), name='save_academic_info'),
    path('save-transcripts/', SaveTranscriptsView.as_view(), name='save_transcripts'),
    path('evaluate-graduation/', EvaluateGraduationView.as_view(), name='evaluate_graduation'),
]