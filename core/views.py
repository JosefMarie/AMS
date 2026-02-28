from django.shortcuts import render, redirect, get_object_or_404
import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse # For PDF
from django.template.loader import render_to_string
from django.contrib.auth import login, logout
from django.contrib import messages
import json
from django.forms import inlineformset_factory

try:
    from weasyprint import HTML
except (ImportError, OSError):
    # Handles "dlopen" or "missing library" errors on Windows/Linux
    HTML = None

from .models import SessionPlan, Activity, CustomUser, StudentProfile

def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):
    from .models import Classroom, Module, StudentProfile, StudentMark, SessionPlan, Attendance
    from django.db.models import Avg, Q
    user = request.user
    context = {}
    if user.role == CustomUser.Role.ADMIN:
        context['student_count'] = StudentProfile.objects.count()
        context['teacher_count'] = CustomUser.objects.filter(role=CustomUser.Role.TEACHER).count()
        context['boy_count'] = StudentProfile.objects.filter(sex='Male').count()
        context['girl_count'] = StudentProfile.objects.filter(sex='Female').count()
        context['classroom_count'] = Classroom.objects.count()
        context['module_count'] = Module.objects.count()
        
        # Teacher Management Search and List
        search_query = request.GET.get('q', '')
        trainers = CustomUser.objects.filter(role=CustomUser.Role.TEACHER)
        if search_query:
            trainers = trainers.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        context['trainers'] = trainers
        context['search_query'] = search_query
        
        recent_sessions = SessionPlan.objects.all().select_related('teacher').order_by('-created_at')[:5]
        # Attach presentation attributes
        for s in recent_sessions:
            s.s_topic = s.topic
            s.s_teacher = s.teacher.username
            s.s_type = s.template_type
            s.s_date = s.created_at.strftime("%b %d")
        context['recent_sessions'] = recent_sessions

        # Chart Data Aggregation
        # (imports moved to top of function)

        # 1. Performance Trends: Average score per module
        module_performance = StudentMark.objects.values('assessment__module__module_name')\
            .annotate(avg_score=Avg('score'), avg_total=Avg('total_marks'))\
            .order_by('-avg_score')[:7]
        
        perf_labels = []
        perf_data = []
        for item in module_performance:
            if item['assessment__module__module_name']:
                perf_labels.append(item['assessment__module__module_name'])
                # Calculate percentage
                percent = (item['avg_score'] / item['avg_total'] * 100) if item['avg_total'] > 0 else 0
                perf_data.append(round(percent, 1))
        
        context['perf_labels_json'] = json.dumps(perf_labels)
        context['perf_data_json'] = json.dumps(perf_data)

        # 2. Demographic Distribution
        demo_data = [context['boy_count'], context['girl_count']]
        context['demo_data_json'] = json.dumps(demo_data)

        # 3. Enrollment Growth (Last 6 Months)
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        growth_labels = []
        growth_data = []
        
        for i in range(5, -1, -1):
            # Approximate months by 30 days for simplicity in logic
            month_start = (now - timedelta(days=i*30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            count = CustomUser.objects.filter(
                role=CustomUser.Role.STUDENT,
                date_joined__range=(month_start, month_end)
            ).count()
            
            growth_labels.append(month_start.strftime("%b %Y"))
            growth_data.append(count)
            
        context['growth_labels_json'] = json.dumps(growth_labels)
        context['growth_data_json'] = json.dumps(growth_data)

        # System Settings
        from .models import SystemSetting
        context['settings'] = SystemSetting.get_settings()

        return render(request, 'dashboard_admin.html', context)
    elif user.role == CustomUser.Role.TEACHER:
        sessions = SessionPlan.objects.filter(teacher=user).order_by('-created_at')[:5]
        for s in sessions:
            s.stype = s.template_type
            s.stopic = s.topic
            s.sdate = s.created_at.strftime("%b %d")
        context['my_sessions'] = sessions
        
        classrooms = Classroom.objects.filter(teacher=user)
        total_students = 0
        for c in classrooms:
            c.cname = c.name
            c.scount = c.students.count()
            c.mcount = c.modules.count()
            total_students += c.scount
        context['my_classrooms'] = classrooms
        context['total_students'] = total_students

        # Metrics Calculations
        # 1. Avg Attendance
        all_attendance = Attendance.objects.filter(classroom__teacher=user)
        total_att = all_attendance.count()
        present_att = all_attendance.filter(status__in=['PRESENT', 'LATE']).count()
        context['avg_attendance'] = round((present_att / total_att * 100), 1) if total_att > 0 else 0

        # Gender Breakdown for Overview
        teacher_students = StudentProfile.objects.filter(classroom__teacher=user)
        context['total_boys'] = teacher_students.filter(sex='Male').count()
        context['total_girls'] = teacher_students.filter(sex='Female').count()

        # 2. Avg Score
        avg_score = StudentMark.objects.filter(assessment__module__teacher=user).aggregate(Avg('score'), Avg('total_marks'))
        if avg_score['score__avg'] and avg_score['total_marks__avg']:
            context['avg_score'] = round((avg_score['score__avg'] / avg_score['total_marks__avg'] * 100), 1)
        else:
            context['avg_score'] = 0

        return render(request, 'dashboard_teacher.html', context)
    elif user.role == CustomUser.Role.STUDENT:
        marks = StudentMark.objects.filter(student=user).order_by('-date_recorded')[:10]
        # Attach presentation attributes to marks
        for m in marks:
            m.status_label = "Completed"
            m.status_class = "bg-emerald-50 text-emerald-600 border border-emerald-100"
            m.m_max = m.total_max if hasattr(m, 'total_max') and m.total_max else (m.assessment.total_marks if m.assessment else 100)
            m.m_name = m.assessment.module_name if m.assessment and hasattr(m.assessment, 'module_name') and m.assessment.module_name else "CORE MODULE"
        # Announcements for student's classroom
        from .models import Announcement
        classroom = user.student_profile.classroom if hasattr(user, 'student_profile') else None
        if classroom:
            context['announcements'] = Announcement.objects.filter(classroom=classroom)[:5]
        else:
            context['announcements'] = []

        context['marks'] = marks
        context['ufirst'] = user.username[0].upper() if user.username else "U"
        context['sid'] = user.student_profile.student_id if hasattr(user, 'student_profile') and user.student_profile and user.student_profile.student_id else "STU-2026-X"
        return render(request, 'dashboard_student.html', context)
@login_required
def admin_settings(request):
    if request.user.role != CustomUser.Role.ADMIN:
        return redirect('dashboard')
    
    from .models import SystemSetting, AuditLog
    from .forms import SystemSettingForm
    
    settings = SystemSetting.get_settings()
    if request.method == 'POST':
        form = SystemSettingForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                user=request.user,
                action="Updated System Settings",
                details="Configuration changed via Admin Settings UI"
            )
            return redirect('admin_settings')
    else:
        form = SystemSettingForm(instance=settings)
    
    return render(request, 'admin_settings.html', {'form': form, 'settings': settings})

@login_required
def security_logs(request):
    if request.user.role != CustomUser.Role.ADMIN:
        return redirect('dashboard')
    
    from .models import AuditLog
    logs = AuditLog.objects.all()[:100]
    return render(request, 'security_logs.html', {'logs': logs})

@login_required
def create_session_plan(request, template_type):
    from .forms import SessionPlanForm, ActivityFormSet

    if request.method == 'POST':
        form = SessionPlanForm(request.POST)
        formset = ActivityFormSet(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.teacher = request.user
            session.template_type = template_type
            session.save()
            
            # Save Formset with instance
            formset.instance = session
            if formset.is_valid():
                formset.save()
                return redirect('dashboard')
    else:
        form = SessionPlanForm()
        # Pre-fill steps based on template type
        initial_data = []
        if template_type == 'THEORY':
            initial_data = [
                {'step_name': 'Introduction (Review/Connect)'},
                {'step_name': 'Development (Jig-saw: Home Groups)'},
                {'step_name': 'Development (Jig-saw: Expert Groups)'},
                {'step_name': 'Development (Jig-saw: Sharing)'},
                {'step_name': 'Conclusion (Summary/Assessment)'}
            ]
        elif template_type == 'PRACTICAL':
             initial_data = [
                {'step_name': 'Preparation (Motivation/Objectives)'},
                {'step_name': 'Demonstration (I do it)'},
                {'step_name': 'Guided Practice (We do it)'},
                {'step_name': 'Independent Practice (You do it)'},
                {'step_name': 'Evaluation (Feedback)'}
            ]
        
        ActivityFormSet = inlineformset_factory(SessionPlan, Activity, fields=['step_name', 'trainer_activity', 'learner_activity', 'time_allocation', 'resources_needed'], extra=len(initial_data), can_delete=True)
        formset = ActivityFormSet(initial=initial_data)

    return render(request, 'create_session_plan.html', {
        'form': form, 
        'formset': formset, 
        'template_type': template_type
    })

@login_required
def view_session_pdf(request, session_id):
    session = get_object_or_404(SessionPlan, id=session_id)
    # Render Template
    template_name = 'pdf_template_theory.html' if session.template_type == 'THEORY' else 'pdf_template_practical.html'
    html_string = render_to_string(template_name, {'session': session, 'user': request.user})

    if HTML:
        html = HTML(string=html_string)
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{session.topic}.pdf"'
        return response
    else:
        return HttpResponse("WeasyPrint not installed or configured.", status=500)

@login_required
def generate_quiz_view(request):
    from .utils import generate_quiz_from_text
    context = {}
    if request.method == 'POST':
        syllabus_text = request.POST.get('syllabus_text', '')
        if syllabus_text:
            quiz_data = generate_quiz_from_text(syllabus_text)
            context['quiz_data'] = quiz_data
            context['syllabus_text'] = syllabus_text
    
    return render(request, 'generate_quiz.html', context)

@login_required
def generate_session_plan_view(request):
    from .utils import generate_session_plan_ai
    from .models import SessionPlan, Activity
    
    if request.method == 'POST':
        syllabus_text = request.POST.get('syllabus_text', '')
        range_text = request.POST.get('range_text', '')
        template_type = request.POST.get('template_type', 'THEORY')
        
        # New manual fields
        extra_data = {
            'sector': request.POST.get('sector', ''),
            'trade': request.POST.get('trade', ''),
            'level': request.POST.get('level', ''),
            'class_name': request.POST.get('class_name', ''),
            'num_students': request.POST.get('num_students', 0),
            'academic_year': request.POST.get('academic_year', '2025/2026'),
            'term': request.POST.get('term', 'Term 1'),
            'weeks': request.POST.get('weeks', '1'),
            'module_name': request.POST.get('module_name', ''),
            'learning_outcome': request.POST.get('learning_outcome', ''),
            'indicative_content': request.POST.get('indicative_content', ''),
            'range_details': request.POST.get('range_details', ''),
            'topic': range_text,
            'duration': request.POST.get('duration', '60'),
            'facilitation_technique': request.POST.get('facilitation_technique', 'Brainstorming'),
            'trainer_name': request.POST.get('trainer_name', ''),
            'performance_criteria': request.POST.get('performance_criteria', ''),
            'pre_requisite_knowledge': request.POST.get('pre_requisite_knowledge', '')
        }
        
        if syllabus_text and range_text:
            # Generate Data
            plan_data = generate_session_plan_ai(syllabus_text, range_text, template_type, **extra_data)
            
            # Save Session Plan
            session = SessionPlan.objects.create(
                teacher=request.user,
                template_type=template_type,
                sector=plan_data['sector'],
                trade=plan_data['trade'],
                level=plan_data['level'],
                class_name=plan_data['class_name'],
                num_students=plan_data['num_students'] if plan_data['num_students'] else 0,
                trainer_name=plan_data['trainer_name'],
                academic_year=plan_data['academic_year'],
                term=plan_data['term'],
                weeks=plan_data['weeks'],
                module=plan_data['module'],
                learning_outcome=plan_data['learning_outcome'],
                indicative_content=plan_data.get('indicative_content', ''),
                topic=plan_data['topic'],
                objectives=plan_data['objectives'],
                performance_criteria=plan_data.get('performance_criteria', ''),
                pre_requisite_knowledge=plan_data.get('pre_requisite_knowledge', ''),
                cross_cutting_issues=plan_data.get('cross_cutting_issues', ''),
                hse_considerations=plan_data.get('hse_considerations', ''),
                ict_tools=plan_data.get('ict_tools', ''),
                special_needs_support=plan_data.get('special_needs_support', ''),
                facilitation_technique=plan_data['facilitation_technique'],
                resources=plan_data['resources'],
                range_details=plan_data.get('range_details', ''),
                duration=plan_data.get('duration', ''),
                reflection=plan_data.get('reflection', '')
            )
            
            # Save Activities
            for act in plan_data['activities']:
                Activity.objects.create(
                    session=session,
                    step_name=act['step_name'],
                    trainer_activity=act['trainer'],
                    learner_activity=act['learner'],
                    time_allocation=act['time']
                )
            
            messages.success(request, f"Session plan for '{plan_data['topic']}' generated successfully!")
            return redirect('dashboard')
            
    return render(request, 'generate_session_plan.html')

@login_required
def generate_advanced_session_plan_view(request):
    from .utils import generate_advanced_session_plan_ai
    from .models import SessionPlan, Activity
    
    if request.method == 'POST':
        syllabus_text = request.POST.get('syllabus_text', '')
        range_text = request.POST.get('range_text', '')
        template_type = request.POST.get('template_type', 'THEORY')
        
        extra_data = {
            'sector': request.POST.get('sector', ''),
            'trade': request.POST.get('trade', ''),
            'level': request.POST.get('level', ''),
            'class_name': request.POST.get('class_name', ''),
            'num_students': request.POST.get('num_students', 0),
            'academic_year': request.POST.get('academic_year', '2025/2026'),
            'term': request.POST.get('term', 'Term 1'),
            'weeks': request.POST.get('weeks', '1'),
            'module_name': request.POST.get('module_name', ''),
            'learning_outcome': request.POST.get('learning_outcome', ''),
            'indicative_content': request.POST.get('indicative_content', ''),
            'range_details': request.POST.get('range_details', ''),
            'topic': range_text,
            'duration': request.POST.get('duration', '60'),
            'facilitation_technique': request.POST.get('facilitation_technique', 'Brainstorming'),
            'trainer_name': request.POST.get('trainer_name', ''),
            'performance_criteria': request.POST.get('performance_criteria', ''),
            'pre_requisite_knowledge': request.POST.get('pre_requisite_knowledge', '')
        }
        
        if syllabus_text and range_text:
            plan_data = generate_advanced_session_plan_ai(syllabus_text, range_text, template_type, **extra_data)
            
            session = SessionPlan.objects.create(
                teacher=request.user,
                template_type=template_type,
                sector=plan_data['sector'],
                trade=plan_data['trade'],
                level=plan_data['level'],
                class_name=plan_data['class_name'],
                num_students=plan_data['num_students'] if plan_data['num_students'] else 0,
                trainer_name=plan_data['trainer_name'],
                academic_year=plan_data['academic_year'],
                term=plan_data['term'],
                weeks=plan_data['weeks'],
                module=plan_data['module'],
                learning_outcome=plan_data['learning_outcome'],
                indicative_content=plan_data.get('indicative_content', ''),
                topic=plan_data['topic'],
                objectives=plan_data['objectives'],
                performance_criteria=plan_data.get('performance_criteria', ''),
                pre_requisite_knowledge=plan_data.get('pre_requisite_knowledge', ''),
                cross_cutting_issues=plan_data.get('cross_cutting_issues', ''),
                hse_considerations=plan_data.get('hse_considerations', ''),
                ict_tools=plan_data.get('ict_tools', ''),
                special_needs_support=plan_data.get('special_needs_support', ''),
                facilitation_technique=plan_data['facilitation_technique'],
                resources=plan_data['resources'],
                range_details=plan_data.get('range_details', ''),
                duration=plan_data.get('duration', ''),
                reflection=plan_data.get('reflection', '')
            )
            
            for act in plan_data['activities']:
                Activity.objects.create(
                    session=session,
                    step_name=act['step_name'],
                    trainer_activity=act['trainer'],
                    learner_activity=act['learner'],
                    time_allocation=act['time']
                )
            
            messages.success(request, f"Advanced session plan for '{plan_data['topic']}' generated successfully!")
            return redirect('dashboard')
            
    return render(request, 'generate_advanced_session_plan.html')

@login_required
def create_assessment_view(request):
    from .forms import AssessmentForm
    if request.method == 'POST':
        form = AssessmentForm(request.user, request.POST)
        if form.is_valid():
            assessment = form.save()
            return redirect('enter_marks', assessment_id=assessment.id)
    else:
        form = AssessmentForm(request.user)
    
    return render(request, 'create_assessment.html', {'form': form})

@login_required
def enter_marks_view(request, assessment_id):
    from .models import Assessment, StudentMark, StudentProfile
    from .forms import StudentMarkFormSet
    
    assessment = get_object_or_404(Assessment, id=assessment_id)
    # Ensure teacher owns the module
    if assessment.module.teacher != request.user:
        return redirect('dashboard')
        
    # Get students in the module's classroom
    classroom = assessment.module.classroom
    students = classroom.students.all() # StudentProfile objects
    
    # Pre-populate marks if they don't exist
    for profile in students:
        StudentMark.objects.get_or_create(
            student=profile.user,
            assessment=assessment,
            defaults={'total_marks': assessment.total_marks, 'score': 0}
        )
    
    queryset = StudentMark.objects.filter(assessment=assessment)
    
    if request.method == 'POST':
        formset = StudentMarkFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            marks = formset.save(commit=False)
            from .models import Notification
            for mark in marks:
                if mark.score > assessment.total_marks:
                    pass # validation handled in template/model?
                mark.save()
                
                # Create Notification for student
                Notification.objects.create(
                    user=mark.student,
                    message=f"New marks entered for {assessment.title}: {mark.score}/{assessment.total_marks}",
                    notification_type=Notification.NotificationType.INFO
                )
                
            return redirect('dashboard')
    else:
        formset = StudentMarkFormSet(queryset=queryset)
        
    marks_with_forms = []
    for form in formset:
        marks_with_forms.append({
            'form': form,
            'student_name': form.instance.student.get_full_name() or form.instance.student.username,
            'student_id': getattr(form.instance.student.student_profile, 'student_id', 'N/A')
        })
        
    return render(request, 'enter_marks.html', {
        'assessment': assessment,
        'formset': formset,
        'marks_with_forms': marks_with_forms
    })

@login_required
def take_attendance_view(request):
    from .models import Classroom
    if request.user.role == CustomUser.Role.STUDENT:
        return redirect('dashboard')
    
    classrooms = Classroom.objects.filter(teacher=request.user)
    return render(request, 'select_attendance_class.html', {'classrooms': classrooms})

@login_required
def perform_attendance_view(request, class_id):
    from .models import StudentProfile, Attendance, Classroom
    import datetime
    
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    date_str = request.GET.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    
    if request.method == 'POST':
        if 'load_date' in request.POST:
             date_str = request.POST.get('date')
             return redirect(f"{request.path}?date={date_str}")
        elif 'save_attendance' in request.POST:
            date_str = request.POST.get('date')
            from .models import Notification
            for key, value in request.POST.items():
                if key.startswith('status_'):
                    student_id = key.split('_')[1] # This is User ID
                    # We need to ensure we are getting the User
                    try:
                        student = CustomUser.objects.get(id=student_id)
                        Attendance.objects.update_or_create(
                            student=student,
                            date=date_str,
                            defaults={
                                'status': value,
                                'teacher': request.user,
                                'classroom': classroom
                            }
                        )
                        # Create Notification for student
                        Notification.objects.create(
                            user=student,
                            message=f"Attendance marked as {value} for {date_str}",
                            notification_type=Notification.NotificationType.INFO
                        )
                    except CustomUser.DoesNotExist:
                        continue
            messages.success(request, f"Attendance saved for {date_str}.")
            return redirect('manage_attendance', class_id=class_id)

    # Load existing attendance
    attendance_records = Attendance.objects.filter(classroom=classroom, date=date_str)
    attendance_dict = {record.student_id: record.status for record in attendance_records}

    # Pre-calculate student info
    profiles = classroom.students.all().select_related('user')
    students_data = []
    for p in profiles:
        students_data.append({
            'id': p.user.id,
            'sid': p.student_id or "N/A",
            'name': p.user.username,
            'status': attendance_dict.get(p.user.id, 'PRESENT')
        })
    
    return render(request, 'take_attendance.html', {
        'classroom': classroom,
        'students': students_data,
        'date': date_str
    })

@login_required
def manage_class_view(request, class_id):
    from .models import Classroom, Assessment, StudentMark, Attendance
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    modules = classroom.modules.all()
    # Pre-calculate student data to avoid template logic breakage
    profiles = classroom.students.all().select_related('user')
    students_list = []
    for p in profiles:
        students_list.append({
            'sid': p.student_id or "Pending",
            'full_name': f"{p.user.first_name} {p.user.last_name}" if p.user.first_name else p.user.username,
            'uname': p.user.username,
            'sex': p.sex,
            'sex_class': "bg-blue-50 text-blue-600" if p.sex == 'Male' else "bg-pink-50 text-pink-600",
            'uid': p.user.id
        })
    
    # Fetch all assessments for this classroom's modules
    assessments = Assessment.objects.filter(module__classroom=classroom).select_related('module').order_by('-created_at')
    assessments_data = []
    for assessment in assessments:
        # Get all marks for this assessment
        marks = StudentMark.objects.filter(assessment=assessment).select_related('student', 'student__student_profile')
        marks_list = []
        for mark in marks:
            marks_list.append({
                'id': mark.id,
                'student_name': mark.student.get_full_name() or mark.student.username,
                'student_id': getattr(mark.student.student_profile, 'student_id', 'N/A') if hasattr(mark.student, 'student_profile') else 'N/A',
                'score': mark.score,
                'total': mark.total_marks,
                'percentage': round((mark.score / mark.total_marks * 100), 1) if mark.total_marks > 0 else 0
            })
        
        assessments_data.append({
            'id': assessment.id,
            'title': assessment.title,
            'module_name': assessment.module.module_name if assessment.module else 'N/A',
            'type': assessment.get_assessment_type_display(),
            'total_marks': assessment.total_marks,
            'marks': marks_list,
            'marks_count': len(marks_list)
        })
    
    # Calculate Avg Attendance for this class
    class_att = Attendance.objects.filter(classroom=classroom)
    total_class_att = class_att.count()
    present_class_att = class_att.filter(status__in=['PRESENT', 'LATE']).count()
    class_avg_attendance = round((present_class_att / total_class_att * 100), 1) if total_class_att > 0 else 0

    # Gender Breakdown for Class
    boys_count = profiles.filter(sex='Male').count()
    girls_count = profiles.filter(sex='Female').count()
    
    return render(request, 'manage_class.html', {
        'classroom': classroom,
        'modules': modules,
        'students': students_list,
        'assessments': assessments_data,
        'avg_attendance': class_avg_attendance,
        'boys_count': boys_count,
        'girls_count': girls_count
    })

@login_required
def create_class_view(request):
    from .models import Classroom
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Classroom.objects.create(name=name, teacher=request.user)
        return redirect('dashboard')
    return redirect('dashboard') # Fallback

@login_required
def add_module_view(request, class_id):
    from .models import Classroom, Module
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    if request.method == 'POST':
        code = request.POST.get('module_code')
        name = request.POST.get('module_name')
        Module.objects.create(classroom=classroom, module_code=code, module_name=name, teacher=request.user)
    return redirect('manage_class', class_id=class_id)

@login_required
def add_student_view(request, class_id):
    from .models import Classroom, CustomUser, StudentProfile
    import random
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        sex = request.POST.get('sex')
        username = request.POST.get('username')
        
        if not username:
            # Auto-generate username: first.last + random
            username = f"{first_name.lower()}.{last_name.lower()}{random.randint(10,99)}"
            
        # Create User
        # Check if exists?
        while CustomUser.objects.filter(username=username).exists():
             username = f"{first_name.lower()}.{last_name.lower()}{random.randint(100,999)}"
        
        user = CustomUser.objects.create_user(username=username, password='password123', first_name=first_name, last_name=last_name, role=CustomUser.Role.STUDENT)
        
        # Create Profile (Auto ID generation happens in save())
        # We need to manually set the classroom
        profile, created = StudentProfile.objects.get_or_create(user=user)
        profile.classroom = classroom
        profile.sex = sex
        profile.save()
        
    return redirect('manage_class', class_id=class_id)

@login_required
def student_report_view(request, student_id):
    from .models import CustomUser, StudentMark, Attendance
    from collections import defaultdict
    
    student = get_object_or_404(CustomUser, id=student_id)
    # Security: Teacher must own the class or Student must be the user
    if request.user.role == CustomUser.Role.STUDENT and request.user.id != student_id:
        return redirect('dashboard')
    
    # Marks logic
    marks = StudentMark.objects.filter(student=student).select_related('assessment__module').order_by('assessment__module')
    
    # Group marks by module
    module_reports = defaultdict(lambda: {'marks': [], 'avg': 0})
    for mark in marks:
        module = mark.assessment.module
        m_id = module.id if module else 0
        m_name = module.module_name if module else "Core Module"
        m_code = module.module_code if module else "CORE"
        
        module_reports[(m_id, m_name, m_code)]['marks'].append(mark)
        
    # Calculate averages and presentation labels
    for key in module_reports:
        m_data = module_reports[key]
        m_marks = m_data['marks']
        if m_marks:
            total_score = sum(m.score for m in m_marks)
            total_possible = sum(m.assessment.total_marks for m in m_marks)
            m_data['avg'] = (total_score / total_possible * 100) if total_possible > 0 else 0
            m_data['competent'] = m_data['avg'] >= 70
            m_data['status_label'] = "Competent" if m_data['competent'] else "Not Yet Competent"
            m_data['status_class'] = "bg-emerald-50 text-emerald-600" if m_data['competent'] else "bg-orange-50 text-orange-600"
            
            # Add type classes to individual marks
            for m in m_marks:
                atype = m.assessment.assessment_type if m.assessment else 'FA'
                if atype == 'FA':
                    m.type_class = "bg-blue-50 text-blue-600"
                elif atype == 'IA':
                    m.type_class = "bg-purple-50 text-purple-600"
                else:
                    m.type_class = "bg-emerald-50 text-emerald-600"

    # Attendance logic
    total_attendance = Attendance.objects.filter(student=student).count()
    present_attendance = Attendance.objects.filter(student=student, status__in=['PRESENT', 'LATE']).count()
    attendance_pct = (present_attendance / total_attendance * 100) if total_attendance > 0 else 0
    
    # SVG Chart Offset Calculation (Circumference = 364.4)
    attendance_offset = 364.4 - (364.4 * attendance_pct / 100)
    
    context = {
        's': student,
        'sname': student.get_full_name() if hasattr(student, 'get_full_name') and student.get_full_name() else student.username,
        'sid': getattr(student.student_profile, 'student_id', 'N/A') if hasattr(student, 'student_profile') and student.student_profile else 'N/A',
        'module_reports': dict(module_reports),
        'apct': f"{attendance_pct:.1f}",
        'aoff': attendance_offset,
        'tatt': total_attendance,
        'patt': present_attendance,
    }
    
    return render(request, 'student_report.html', context)

@login_required
def student_transcript_pdf_view(request, student_id):
    import datetime
    from .models import CustomUser, StudentMark, Attendance
    from collections import defaultdict
    
    student = get_object_or_404(CustomUser, id=student_id)
    
    marks = StudentMark.objects.filter(student=student).select_related('assessment__module')
    
    module_data = defaultdict(lambda: {'fa': 0, 'ia': 0, 'sa': 0, 'total_score': 0, 'total_max': 0, 'marks_count': 0})
    for mark in marks:
        module = mark.assessment.module
        m_name = module.module_name if module else "Core"
        
        module_data[m_name]['total_score'] += mark.score
        module_data[m_name]['total_max'] += mark.assessment.total_marks
        module_data[m_name]['marks_count'] += 1
        
        normalized_score = (mark.score / mark.assessment.total_marks) * 100
        if mark.assessment.assessment_type == 'FA': module_data[m_name]['fa'] = normalized_score
        elif mark.assessment.assessment_type == 'IA': module_data[m_name]['ia'] = normalized_score
        elif mark.assessment.assessment_type == 'SA': module_data[m_name]['sa'] = normalized_score

    for m in module_data:
        max_marks = module_data[m]['total_max']
        avg = (module_data[m]['total_score'] / max_marks * 100) if max_marks > 0 else 0
        module_data[m]['avg'] = f"{avg:.1f}"
        module_data[m]['comp'] = avg >= 70
        module_data[m]['fa'] = f"{module_data[m]['fa']:.0f}"
        module_data[m]['ia'] = f"{module_data[m]['ia']:.0f}"
        module_data[m]['sa'] = f"{module_data[m]['sa']:.0f}"

    html_string = render_to_string('pdf_student_transcript.html', {
        's': student,
        'sname': student.get_full_name() if hasattr(student, 'get_full_name') and student.get_full_name() else student.username,
        'sid': getattr(student.student_profile, 'student_id', 'N/A') if hasattr(student, 'student_profile') and student.student_profile else 'N/A',
        'mdata': dict(module_data),
        'idate': datetime.date.today().strftime("%b %d, %Y"),
        'user': request.user
    })

    if HTML:
        html = HTML(string=html_string)
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Transcript_{student.username}.pdf"'
        return response
    return HttpResponse("PDF generator error", status=500)

@login_required
def edit_mark_view(request, mark_id):
    from .models import StudentMark
    mark = get_object_or_404(StudentMark, id=mark_id)
    # Verify teacher owns this class
    classroom_id = mark.assessment.module.classroom.id
    if mark.assessment.module.classroom.teacher != request.user:
        messages.error(request, "You do not have permission to edit this mark.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            new_score = float(request.POST.get('score'))
            mark.score = new_score
            mark.save()
            messages.success(request, f"Mark updated successfully for {mark.student.username}.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid score value.")
        return redirect('manage_class', class_id=classroom_id)
    
    return redirect('manage_class', class_id=classroom_id)

@login_required
def delete_mark_view(request, mark_id):
    from .models import StudentMark
    mark = get_object_or_404(StudentMark, id=mark_id)
    # Verify teacher owns this class
    classroom_id = mark.assessment.module.classroom.id
    if mark.assessment.module.classroom.teacher != request.user:
        messages.error(request, "You do not have permission to delete this mark.")
        return redirect('dashboard')
    
    student_name = mark.student.username
    mark.delete()
    messages.success(request, f"Mark deleted successfully for {student_name}.")
    return redirect('manage_class', class_id=classroom_id)

@login_required
def delete_session_view(request, session_id):
    from .models import SessionPlan
    session = get_object_or_404(SessionPlan, id=session_id)
    # Verify teacher owns this session
    if session.teacher != request.user:
        messages.error(request, "You do not have permission to delete this session.")
        return redirect('dashboard')
    
    session_title = session.topic
    session.delete()
    messages.success(request, f"Session plan '{session_title}' deleted successfully.")
    return redirect('dashboard')

@login_required
def add_student_view(request, class_id):
    from .models import Classroom, StudentProfile
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        sex = request.POST.get('sex')
        
        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f"User with username '{username}' already exists.")
            return redirect('manage_class', class_id=class_id)
        
        # Create the student user
        student = CustomUser.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=CustomUser.Role.STUDENT,
            password='student123'  # Default password
        )
        student.sex = sex
        student.save()
        
        # Create student profile
        StudentProfile.objects.create(
            user=student,
            classroom=classroom,
            sex=sex
        )
        
        messages.success(request, f"Student '{student.get_full_name() or username}' added successfully. Default password: student123")
        return redirect('manage_class', class_id=class_id)
    
    return render(request, 'add_student.html', {'classroom': classroom})

@login_required
def add_module_view(request, class_id):
    from .models import Classroom, Module
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    
    if request.method == 'POST':
        module_code = request.POST.get('module_code')
        module_name = request.POST.get('module_name')
        
        # Check if module with same code already exists for this classroom
        if Module.objects.filter(classroom=classroom, module_code=module_code).exists():
            messages.error(request, f"Module with code '{module_code}' already exists in this classroom.")
            return redirect('manage_class', class_id=class_id)
        
        # Create the module
        Module.objects.create(
            classroom=classroom,
            module_code=module_code,
            module_name=module_name,
            teacher=request.user
        )
        
        messages.success(request, f"Module '{module_code} - {module_name}' added successfully.")
        return redirect('manage_class', class_id=class_id)
    
    return render(request, 'add_module.html', {'classroom': classroom})

@login_required
def generate_quiz_view(request):
    from .models import Module, Assessment
    from .ai_quiz_generator import generate_quiz_with_ai
    import json
    
    # Get all modules taught by this teacher
    modules = Module.objects.filter(teacher=request.user)
    modules_data = [{'id': m.id, 'code': m.module_code, 'name': m.module_name} for m in modules]
    
    quiz_data = None
    syllabus_text = ''
    assessment_id = None
    
    if request.method == 'POST':
        module_id = request.POST.get('module_id')
        quiz_type = request.POST.get('quiz_type')
        duration = request.POST.get('duration')
        syllabus_text = request.POST.get('syllabus_text', '')
        
        # Get question counts
        try:
            num_mcq = int(request.POST.get('num_mcq', 10))
            num_tf = int(request.POST.get('num_tf', 5))
            num_matching = int(request.POST.get('num_matching', 5))
        except ValueError:
            num_mcq, num_tf, num_matching = 10, 5, 5
        
        if module_id and quiz_type and duration and syllabus_text:
            # Generate quiz using AI
            quiz_data = generate_quiz_with_ai(syllabus_text, num_mcq, num_tf, num_matching)
            
            # Save as Assessment
            module = Module.objects.get(id=module_id)
            quiz_type_display = "Formative Assessment" if quiz_type == "FA" else "Summative Assessment"
            
            # Calculate total marks (MCQ=1, TF=1, Matching=1)
            total_marks = (len(quiz_data.get('mcq', [])) * 1) + \
                          (len(quiz_data.get('true_false', [])) * 1) + \
                          (len(quiz_data.get('matching', [])) * 1)
            
            assessment = Assessment.objects.create(
                module=module,
                title=f"{module.module_code} - AI Generated {quiz_type_display}",
                assessment_type=quiz_type,
                total_marks=float(total_marks),
                questions_json=json.dumps(quiz_data)
            )
            assessment_id = assessment.id
            messages.success(request, f"Quiz generated successfully! Total Marks: {total_marks}")
    
    return render(request, 'generate_quiz.html', {
        'modules': modules_data,
        'quiz_data': quiz_data,
        'syllabus_text': syllabus_text,
        'assessment_id': assessment_id
    })

@login_required
def view_quiz_pdf(request, assessment_id):
    from .models import Assessment
    import json
    
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Verify teacher has access
    if assessment.module.teacher != request.user:
        messages.error(request, "You do not have permission to view this quiz.")
        return redirect('dashboard')
    
    # Parse quiz data
    try:
        quiz_data = json.loads(assessment.questions_json) if assessment.questions_json else {}
    except:
        quiz_data = {}
    
    context = {
        'assessment': assessment,
        'quiz_data': quiz_data,
        'module': assessment.module,
    }
    
    return render(request, 'quiz_pdf.html', context)

@login_required
def create_class_view(request):
    from .models import Classroom
    
    if request.method == 'POST':
        class_name = request.POST.get('class_name')
        
        if class_name:
            Classroom.objects.create(
                name=class_name,
                teacher=request.user
            )
            messages.success(request, f"Classroom '{class_name}' created successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Class name is required.")
            
    return render(request, 'create_class.html')
@login_required
def print_student_list_view(request, class_id):
    from .models import Classroom
    import datetime
    
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    students = classroom.students.all().select_related('user').order_by('user__last_name')
    
    html_string = render_to_string('pdf_student_list.html', {
        'classroom': classroom,
        'students': students,
        'date': datetime.date.today().strftime("%B %d, %Y"),
        'user': request.user
    })

    if HTML:
        html = HTML(string=html_string)
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{classroom.name}_Student_List.pdf"'
        return response
    return HttpResponse("PDF generator error", status=500)

@login_required
def delete_assessment_view(request, assessment_id):
    from .models import Assessment
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Verify teacher owns this assessment (via module -> classroom -> teacher)
    if assessment.module.teacher != request.user:
        messages.error(request, "You do not have permission to delete this assessment.")
        return redirect('dashboard')
    
    class_id = assessment.module.classroom.id
    title = assessment.title
    assessment.delete()
    messages.success(request, f"Assessment '{title}' deleted successfully.")
    return redirect('manage_class', class_id=class_id)
@login_required
def manage_attendance_view(request, class_id):
    from .models import Classroom, Attendance
    from django.db.models import Count, Q, Max
    
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    
    # Get all distinct dates with attendance for this class
    # Annotate with counts and latest time recorded
    history = Attendance.objects.filter(classroom=classroom).values('date').annotate(
        present_count=Count('id', filter=Q(status='PRESENT')),
        absent_count=Count('id', filter=Q(status='ABSENT')),
        late_count=Count('id', filter=Q(status='LATE')),
        latest_time=Max('time_recorded')
    ).order_by('-date')

    return render(request, 'manage_attendance.html', {
        'classroom': classroom,
        'history': history
    })

@login_required
def delete_attendance_view(request, class_id):
    from .models import Classroom, Attendance
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    date_str = request.POST.get('date') or request.GET.get('date')
    
    if date_str:
        Attendance.objects.filter(classroom=classroom, date=date_str).delete()
        messages.success(request, f"Attendance records for {date_str} deleted.")
    
    return redirect('manage_attendance', class_id=class_id)

@login_required
def edit_student_view(request, student_id):
    from .models import CustomUser, StudentProfile
    student = get_object_or_404(CustomUser, id=student_id, role=CustomUser.Role.STUDENT)
    profile = get_object_or_404(StudentProfile, user=student)
    
    # Security: Ensure teacher owns this classroom
    if profile.classroom.teacher != request.user:
        messages.error(request, "You do not have permission to edit this student.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        sex = request.POST.get('sex')
        
        # Check if username is taken by someone else
        if CustomUser.objects.filter(username=username).exclude(id=student.id).exists():
            messages.error(request, f"Username '{username}' is already taken.")
        else:
            student.first_name = first_name
            student.last_name = last_name
            student.username = username
            student.save()
            
            profile.sex = sex
            profile.save()
            
            AuditLog.objects.create(
                user=request.user,
                action="Updated Student",
                details=f"Updated student {student.username} (ID: {student.id})"
            )
            messages.success(request, f"Student '{student.get_full_name() or username}' updated successfully.")
            return redirect('manage_class', class_id=profile.classroom.id)
            
    return render(request, 'edit_student.html', {
        'student': student,
        'profile': profile,
        'classroom': profile.classroom
    })

@login_required
def delete_student_view(request, student_id):
    from .models import CustomUser, StudentProfile
    student = get_object_or_404(CustomUser, id=student_id, role=CustomUser.Role.STUDENT)
    profile = get_object_or_404(StudentProfile, user=student)
    
    # Security: Ensure teacher owns this classroom
    if profile.classroom.teacher != request.user:
        messages.error(request, "You do not have permission to delete this student.")
        return redirect('dashboard')
    
    class_id = profile.classroom.id
    student_name = student.get_full_name() or student.username
    
    # Delete student (this will cascade to Attendance and StudentMark)
    student.delete()
    from .models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action="Deleted Student",
        details=f"Deleted student {student_name} (ID: {student_id})"
    )
    
    messages.success(request, f"Student '{student_name}' has been deleted from the classroom.")
    return redirect('manage_class', class_id=class_id)

@login_required
def create_teacher_view(request):
    from .forms import TrainerCreationForm
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Only administrators can create teacher accounts.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TrainerCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            from .models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action="Created Trainer",
                details=f"Created trainer account for {user.username}"
            )
            messages.success(request, f"Teacher account for '{user.get_full_name() or user.username}' created successfully!")
            return redirect('dashboard')
    else:
        form = TrainerCreationForm()
    
    return render(request, 'create_trainer.html', {'form': form})

def privacy_policy_view(request):
    return render(request, 'privacy_policy.html')

def terms_of_service_view(request):
    return render(request, 'terms_of_service.html')

@login_required
def change_password_view(request):
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            from .models import AuditLog, Notification
            AuditLog.objects.create(
                user=request.user,
                action="Changed Password",
                details=f"User {user.username} changed their password."
            )
            # Create Notification
            Notification.objects.create(
                user=request.user,
                message="Your password was successfully changed.",
                notification_type=Notification.NotificationType.SUCCESS
            )
            messages.success(request, 'Your password was successfully updated!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {
        'form': form
    })

@login_required
def edit_trainer_view(request, user_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
    
    trainer = get_object_or_404(CustomUser, id=user_id, role=CustomUser.Role.TEACHER)
    
    if request.method == 'POST':
        trainer.username = request.POST.get('username')
        trainer.first_name = request.POST.get('first_name')
        trainer.last_name = request.POST.get('last_name')
        trainer.email = request.POST.get('email')
        trainer.save()
        from .models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action="Updated Trainer",
            details=f"Updated trainer details for {trainer.username} (ID: {user_id})"
        )
        return redirect('dashboard')
        
    return render(request, 'edit_trainer.html', {'trainer': trainer})

@login_required
def delete_trainer_view(request, user_id):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
    
    trainer = get_object_or_404(CustomUser, id=user_id, role=CustomUser.Role.TEACHER)
    trainer_name = trainer.get_full_name() or trainer.username
    trainer.delete()
    from .models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action="Deleted Trainer",
        details=f"Deleted trainer account for {trainer_name}"
    )
    messages.success(request, f"Trainer '{trainer_name}' has been removed from the system.")
    return redirect('dashboard')

@login_required
def broadcast_view(request):
    if request.user.role != CustomUser.Role.TEACHER:
        return redirect('dashboard')
    
    from .models import Announcement, Classroom, AuditLog
    from .forms import AnnouncementForm
    
    announcements = Announcement.objects.filter(teacher=request.user)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.user, request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.teacher = request.user
            announcement.save()
            AuditLog.objects.create(
                user=request.user,
                action="Posted Announcement",
                details=f"Posted: {announcement.title} to {announcement.classroom.name}"
            )
            return redirect('broadcasts')
    else:
        form = AnnouncementForm(request.user)
        
    return render(request, 'broadcasts.html', {
        'form': form,
        'announcements': announcements
    })

@login_required
def interactive_gradebook(request, class_id):
    if request.user.role != CustomUser.Role.TEACHER:
        return redirect('dashboard')
    
    from .models import Classroom, StudentProfile, Module, StudentMark
    classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
    students = StudentProfile.objects.filter(classroom=classroom)
    modules = Module.objects.filter(classroom=classroom)
    
    # Pre-fetch marks for performance
    marks = StudentMark.objects.filter(student__student_profile__in=students, assessment__module__in=modules)
    
    # Build a matrix: student_id -> {module_id -> score}
    score_matrix = {}
    for student in students:
        score_matrix[student.user.id] = {}
        for module in modules:
            # Find the best score for this module/student
            module_marks = [m.score for m in marks if m.student.id == student.user.id and m.assessment.module.id == module.id]
            score_matrix[student.user.id][module.id] = max(module_marks) if module_marks else "-"

    return render(request, 'interactive_gradebook.html', {
        'classroom': classroom,
        'students': students,
        'modules': modules,
        'score_matrix': score_matrix
    })

@login_required
def bulk_grade_import(request):
    if request.user.role != CustomUser.Role.TEACHER:
        return redirect('dashboard')
    
    import csv, io
    from .models import StudentProfile, Module, Assessment, StudentMark, AuditLog
    from django.contrib import messages
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []

            for row in reader:
                try:
                    student_id = row.get('Student ID')
                    module_code = row.get('Module Code')
                    assessment_title = row.get('Assessment')
                    score = row.get('Score')
                    total = row.get('Total')

                    if not student_id or not module_code:
                        continue

                    student_profile = StudentProfile.objects.get(student_id=student_id)
                    module = Module.objects.get(module_code=module_code, classroom=student_profile.classroom)
                    
                    # Get or create assessment
                    assessment, created = Assessment.objects.get_or_create(
                        module=module,
                        title=assessment_title,
                        defaults={'total_marks': total if total else 100}
                    )

                    # Update or create mark
                    StudentMark.objects.update_or_create(
                        student=student_profile.user,
                        assessment=assessment,
                        defaults={'score': score, 'total_marks': assessment.total_marks}
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row error: {str(e)}")

            AuditLog.objects.create(
                user=request.user,
                action="Bulk Grade Import",
                details=f"Imported {success_count} grades, {error_count} errors."
            )
            messages.success(request, f"Successfully imported {success_count} grades.")
            if errors:
                messages.warning(request, f"Encountered {error_count} errors during import.")

            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"File error: {str(e)}")
            return redirect('bulk_grade_import')

    return render(request, 'bulk_import.html')

@login_required
def edit_profile(request):
    from .forms import StudentProfileForm
    from .models import StudentProfile
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('dashboard')
    else:
        form = StudentProfileForm(instance=profile)
    
    return render(request, 'edit_profile.html', {'form': form})

@login_required
def portfolio_view(request, username=None):
    from .models import CustomUser, StudentMark
    from django.db.models import Max
    
    target_user = get_object_or_404(CustomUser, username=username) if username else request.user
    if target_user.role != CustomUser.Role.STUDENT:
        return redirect('dashboard')
        
    profile = getattr(target_user, 'student_profile', None)
    
    # Calculate Top Skills (Top 3 modules with highest scores)
    top_marks = StudentMark.objects.filter(student=target_user)\
        .values('assessment__module__module_name', 'assessment__module__module_code')\
        .annotate(best_score=Max('score'))\
        .order_by('-best_score')[:3]

    return render(request, 'portfolio.html', {
        'student': target_user,
        'profile': profile,
        'top_skills': top_marks
    })

@login_required
def resource_library(request):
    from .models import Resource, Module
    user = request.user
    
    if user.role == CustomUser.Role.STUDENT:
        classroom = getattr(user, 'student_profile', None).classroom if hasattr(user, 'student_profile') else None
        modules = Module.objects.filter(classroom=classroom)
    else:
        modules = Module.objects.filter(teacher=user)
        
    resources = Resource.objects.filter(module__in=modules).select_related('module')
    
    return render(request, 'resource_library.html', {
        'resources': resources,
        'is_teacher': user.role == CustomUser.Role.TEACHER
    })

@login_required
def manage_resources(request):
    if request.user.role != CustomUser.Role.TEACHER:
        return redirect('dashboard')
    
    from .forms import ResourceForm
    from .models import Resource, AuditLog
    
    if request.method == 'POST':
        form = ResourceForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            resource = form.save()
            AuditLog.objects.create(
                user=request.user,
                action="Uploaded Resource",
                details=f"Uploaded: {resource.title} for {resource.module.module_code}"
            )
            messages.success(request, "Resource uploaded successfully!")
            return redirect('resource_library')
    else:
        form = ResourceForm(request.user)
        
    return render(request, 'manage_resources.html', {'form': form})

@login_required
def learning_journey(request):
    if request.user.role != CustomUser.Role.STUDENT:
        return redirect('dashboard')
    
    from .models import Module, StudentMark
    classroom = request.user.student_profile.classroom if hasattr(request.user, 'student_profile') else None
    modules = Module.objects.filter(classroom=classroom)
    marks = StudentMark.objects.filter(student=request.user)
    
    journey = []
    for module in modules:
        # Calculate percentage for each mark and find the best one
        module_marks = marks.filter(assessment__module_id=module.id)
        if module_marks.exists():
            # Calculate percentage for each mark: (score / total_marks) * 100
            percentages = [(m.score / m.total_marks * 100) if m.total_marks > 0 else 0 for m in module_marks]
            best_percent = max(percentages)
            status = 'Mastered' if best_percent >= 80 else 'In Progress'
            score = best_percent
        else:
            status = 'Locked'
            score = 0
            
        journey.append({
            'module': module,
            'status': status,
            'score': score
        })
        
    return render(request, 'learning_journey.html', {'journey': journey})

@login_required
def clear_notifications_view(request):
    from django.http import JsonResponse
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})

@login_required
def ai_study_recommendation_view(request):
    if request.user.role != CustomUser.Role.STUDENT:
        return redirect('dashboard')
        
    from .models import Module, StudentMark
    from .utils import analyze_student_weakness
    
    classroom = request.user.student_profile.classroom if hasattr(request.user, 'student_profile') else None
    modules = Module.objects.filter(classroom=classroom)
    marks = StudentMark.objects.filter(student=request.user)
    
    marks_data = {}
    for module in modules:
        module_marks = marks.filter(assessment__module_id=module.id)
        if module_marks.exists():
            percentages = [(m.score / m.total_marks * 100) if m.total_marks > 0 else 0 for m in module_marks]
            best_percent = max(percentages)
            marks_data[module.module_name] = {'score_percent': best_percent}
        else:
            marks_data[module.module_name] = {'score_percent': 0}
            
    if not marks_data:
        messages.warning(request, "Not enough data for AI analysis.")
        return redirect('dashboard')
        
    analysis = analyze_student_weakness(marks_data)
    
    return render(request, 'student_ai_assistant.html', {
        'marks_data': marks_data,
        'analysis': analysis
    })
