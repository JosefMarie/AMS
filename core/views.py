from django.shortcuts import render, redirect, get_object_or_404
import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse # For PDF
from django.template.loader import render_to_string
from django.contrib.auth import login, logout
from django.contrib import messages
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
    user = request.user
    context = {}
    if user.role == CustomUser.Role.ADMIN:
        context['student_count'] = StudentProfile.objects.count()
        context['teacher_count'] = CustomUser.objects.filter(role=CustomUser.Role.TEACHER).count()
        recent_sessions = SessionPlan.objects.all().select_related('teacher').order_by('-created_at')[:5]
        # Attach presentation attributes
        for s in recent_sessions:
            s.s_topic = s.topic
            s.s_teacher = s.teacher.username
            s.s_type = s.template_type
            s.s_date = s.created_at.strftime("%b %d")
        context['recent_sessions'] = recent_sessions
        return render(request, 'dashboard_admin.html', context)
    elif user.role == CustomUser.Role.TEACHER:
        from .models import Classroom
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
        return render(request, 'dashboard_teacher.html', context)
    elif user.role == CustomUser.Role.STUDENT:
        from .models import StudentMark
        marks = StudentMark.objects.filter(student=user).order_by('-date_recorded')[:10]
        # Attach presentation attributes to marks
        for m in marks:
            m.status_label = "Completed"
            m.status_class = "bg-emerald-50 text-emerald-600 border border-emerald-100"
            m.m_max = m.total_max if hasattr(m, 'total_max') and m.total_max else (m.assessment.total_marks if m.assessment else 100)
            m.m_name = m.assessment.module_name if m.assessment and hasattr(m.assessment, 'module_name') and m.assessment.module_name else "CORE MODULE"
        context['marks'] = marks
        context['ufirst'] = user.username[0].upper() if user.username else "U"
        context['sid'] = user.student_profile.student_id if hasattr(user, 'student_profile') and user.student_profile and user.student_profile.student_id else "STU-2026-X"
        return render(request, 'dashboard_student.html', context)
    return render(request, 'dashboard.html')

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
            for mark in marks:
                if mark.score > assessment.total_marks:
                    pass # validation handled in template/model?
                mark.save()
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
    from .models import Classroom, Assessment, StudentMark
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
    
    return render(request, 'manage_class.html', {
        'classroom': classroom,
        'modules': modules,
        'students': students_list,
        'assessments': assessments_data
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
        total_count=Count('id'),
        latest_time=Max('time_recorded')
    ).order_by('-date')
    
    return render(request, 'manage_attendance.html', {
        'classroom': classroom,
        'history': history
    })

@login_required
def delete_attendance_view(request, class_id):
    from .models import Classroom, Attendance
    if request.method == 'POST':
        date_str = request.POST.get('date')
        classroom = get_object_or_404(Classroom, id=class_id, teacher=request.user)
        
        deleted_count, _ = Attendance.objects.filter(classroom=classroom, date=date_str).delete()
        
        if deleted_count > 0:
            messages.success(request, f"Attendance records for {date_str} deleted successfully.")
        else:
            messages.warning(request, f"No records found to delete for {date_str}.")
            
    return redirect('manage_attendance', class_id=class_id)
