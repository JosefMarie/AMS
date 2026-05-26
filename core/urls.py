from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('timeline/select/', views.timeline_select_view, name='timeline_select'),
    path('academic-year/create/', views.create_academic_year_view, name='create_academic_year'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('session/create/<str:template_type>/', views.create_session_plan, name='create_session_plan'),
    path('session/<int:session_id>/pdf/', views.view_session_pdf, name='view_session_pdf'),
    path('session/edit/<int:session_id>/', views.edit_session_plan_view, name='edit_session_plan'),
    path('student/session/<int:session_id>/', views.student_session_detail_view, name='student_session_detail'),
    path('quiz/generate/', views.generate_quiz_view, name='generate_quiz'),
    path('marks/create/', views.create_assessment_view, name='create_assessment'),
    path('marks/enter/<int:assessment_id>/', views.enter_marks_view, name='enter_marks'),
    path('attendance/take/', views.take_attendance_view, name='take_attendance'),
    path('session/generate/', views.generate_advanced_session_plan_view, name='generate_session_plan'),
    path('session/generate-advanced/', views.generate_advanced_session_plan_view, name='generate_advanced_session_plan'),
    path('sessions/', views.session_plans_list_view, name='session_plans_list'),
    path('perform-attendance/<int:class_id>/', views.perform_attendance_view, name='perform_attendance'),
    path('class/create/', views.create_class_view, name='create_class'),
    path('class/<int:class_id>/', views.manage_class_view, name='manage_class'),
    path('class/<int:class_id>/promote/', views.promote_students_view, name='promote_students'),
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
    path('trainer/create/', views.create_teacher_view, name='create_trainer'),
    path('privacy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms/', views.terms_of_service_view, name='terms_of_service'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('trainer/edit/<int:user_id>/', views.edit_trainer_view, name='edit_trainer'),
    path('trainer/delete/<int:user_id>/', views.delete_trainer_view, name='delete_trainer'),
    path('curriculum/upload/', views.upload_curriculum_view, name='upload_curriculum'),
    path('admin/trade/create/', views.create_trade_view, name='create_trade'),
    
    # Co-teaching & Classroom Sharing
    path('class/<int:classroom_id>/share/request/', views.send_share_request, name='send_share_request'),
    path('share-request/<int:request_id>/<str:action>/', views.respond_share_request, name='respond_share_request'),
    path('class/<int:classroom_id>/co-teacher/add/<int:teacher_id>/', views.add_co_teacher_direct, name='add_co_teacher'),
    path('class/<int:classroom_id>/co-teacher/remove/<int:teacher_id>/', views.remove_co_teacher_view, name='remove_co_teacher'),

    
    # AJAX API Endpoints
    path('api/curriculums/<int:trade_id>/', views.get_curriculums, name='api_get_curriculums'),
    path('api/modules/<int:curriculum_id>/', views.get_modules, name='api_get_modules'),
    path('api/learning_outcomes/<int:module_id>/', views.get_learning_outcomes, name='api_get_learning_outcomes'),
    path('api/indicative_contents/<int:lo_id>/', views.get_indicative_contents, name='api_get_indicative_contents'),
    path('api/topics/<int:ic_id>/', views.get_topics, name='api_get_topics'),
    path('api/save-user-gemini-key/', views.save_user_gemini_key, name='save_user_gemini_key'),
    
    path('admin-settings/', views.admin_settings, name='admin_settings'),
    path('security-logs/', views.security_logs, name='security_logs'),
    path('broadcasts/', views.broadcast_view, name='broadcasts'),
    path('gradebook/bulk-import/', views.bulk_grade_import, name='bulk_grade_import'),
    path('gradebook/<int:class_id>/', views.interactive_gradebook, name='interactive_gradebook'),
    
    # Student Success
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('portfolio/', views.portfolio_view, name='my_portfolio'),
    path('portfolio/<str:username>/', views.portfolio_view, name='portfolio_view'),
    path('resources/', views.resource_library, name='resource_library'),
    path('resources/manage/', views.manage_resources, name='manage_resources'),
    path('journey/', views.learning_journey, name='learning_journey'),
    
    # Notifications API
    path('notifications/clear/', views.clear_notifications_view, name='clear_notifications'),
    
    # AI Education Assistant
    path('student/ai-assistant/', views.ai_study_recommendation_view, name='ai_study_recommendation'),

    # Admin AI testing
    path('admin/test-ai/', views.test_ai_connection_view, name='test_ai_connection'),

    # Manage User Emails
    path('manage-emails/', views.manage_user_emails, name='manage_user_emails'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

    # User Persona Guides
    path('guide/teacher/', views.teacher_persona_view, name='teacher_persona'),
    path('guide/student/', views.student_persona_view, name='student_persona'),
    path('guide/admin/', views.admin_persona_view, name='admin_persona'),

    # Scheme of Work templates (Admin)
    path('manage/scheme-templates/', views.admin_scheme_templates_view, name='admin_scheme_templates'),
    path('manage/scheme-templates/<int:template_id>/delete/', views.delete_scheme_template_view, name='delete_scheme_template'),

    # Schemes of Work (Teacher)
    path('schemes-of-work/', views.scheme_of_work_list_view, name='scheme_of_work_list'),
    path('schemes-of-work/create/', views.scheme_of_work_create_view, name='scheme_of_work_create'),
    path('schemes-of-work/generate-ai/', views.generate_scheme_of_work_ai, name='generate_scheme_of_work_ai'),
    path('schemes-of-work/<int:scheme_id>/edit/', views.scheme_of_work_editor_view, name='scheme_of_work_editor'),
    path('schemes-of-work/<int:scheme_id>/save/', views.scheme_of_work_save, name='scheme_of_work_save'),
    path('schemes-of-work/<int:scheme_id>/print/', views.scheme_of_work_pdf_view, name='scheme_of_work_pdf'),
    path('schemes-of-work/<int:scheme_id>/delete/', views.delete_scheme_of_work, name='delete_scheme_of_work'),
]
