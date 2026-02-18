from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('session/create/<str:template_type>/', views.create_session_plan, name='create_session_plan'),
    path('session/<int:session_id>/pdf/', views.view_session_pdf, name='view_session_pdf'),
    path('quiz/generate/', views.generate_quiz_view, name='generate_quiz'),
    path('marks/create/', views.create_assessment_view, name='create_assessment'),
    path('marks/enter/<int:assessment_id>/', views.enter_marks_view, name='enter_marks'),
    path('attendance/take/', views.take_attendance_view, name='take_attendance'),
    path('session/generate/', views.generate_session_plan_view, name='generate_session_plan'),
    path('perform-attendance/<int:class_id>/', views.perform_attendance_view, name='perform_attendance'),
    path('class/create/', views.create_class_view, name='create_class'),
    path('class/<int:class_id>/', views.manage_class_view, name='manage_class'),
    path('class/<int:class_id>/add_module/', views.add_module_view, name='add_module'),
    path('class/<int:class_id>/add_student/', views.add_student_view, name='add_student'),
    path('student/report/<int:student_id>/', views.student_report_view, name='student_report'),
    path('student/report/pdf/<int:student_id>/', views.student_transcript_pdf_view, name='student_transcript_pdf'),
    path('marks/edit/<int:mark_id>/', views.edit_mark_view, name='edit_mark'),
    path('marks/delete/<int:mark_id>/', views.delete_mark_view, name='delete_mark'),
    path('session/delete/<int:session_id>/', views.delete_session_view, name='delete_session'),
    path('quiz/view/<int:assessment_id>/', views.view_quiz_pdf, name='view_quiz_pdf'),
    path('class/<int:class_id>/print/', views.print_student_list_view, name='print_student_list'),
    path('assessment/delete/<int:assessment_id>/', views.delete_assessment_view, name='delete_assessment'),
    path('class/<int:class_id>/attendance/', views.manage_attendance_view, name='manage_attendance'),
    path('class/<int:class_id>/attendance/delete/', views.delete_attendance_view, name='delete_attendance'),
    path('student/edit/<int:student_id>/', views.edit_student_view, name='edit_student_entry'),
    path('student/delete/<int:student_id>/', views.delete_student_view, name='delete_student_entry'),
]
