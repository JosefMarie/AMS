from django.shortcuts import render, redirect, get_object_or_404
import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse # For PDF
from django.template.loader import render_to_string
from django.contrib.auth import login, logout
from django.contrib import messages
import json
from django.forms import inlineformset_factory
from django.db.models import Q


try:
    from weasyprint import HTML
except (ImportError, OSError):
    # Handles "dlopen" or "missing library" errors on Windows/Linux
    HTML = None

from .models import SessionPlan, Activity, CustomUser, StudentProfile, AuditLog, Classroom, Module, Assessment, StudentMark, Attendance, SystemSetting, Notification, Resource, Announcement, ClassroomShareRequest

def _get_active_timeline(request):
    from .models import AcademicYear, SystemSetting
    settings = SystemSetting.get_settings()
    
    session_year_id = request.session.get('view_year_id')
    session_term = request.session.get('view_term')
    
    active_year = None
    if session_year_id:
        try:
            active_year = AcademicYear.objects.get(pk=session_year_id)
        except AcademicYear.DoesNotExist:
            pass
            
    if not active_year:
        active_year = settings.current_academic_year
    if not active_year:
        active_year = AcademicYear.objects.filter(is_active=True).first() or AcademicYear.objects.all().order_by('-name').first()
        
    active_term = session_term or settings.current_term or 'Term 1'
    return active_year, active_term

def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):
    from .models import Classroom, Module, StudentProfile, StudentMark, SessionPlan, Attendance
    from django.db.models import Avg, Q
    user = request.user
    context = {}
    active_year, active_term = _get_active_timeline(request)
    
    if user.role == CustomUser.Role.ADMIN:
        context['student_count'] = StudentProfile.objects.count()
        context['teacher_count'] = CustomUser.objects.filter(role=CustomUser.Role.TEACHER).count()
        context['boy_count'] = StudentProfile.objects.filter(sex='Male').count()
        context['girl_count'] = StudentProfile.objects.filter(sex='Female').count()
        context['classroom_count'] = Classroom.objects.count()
        context['module_count'] = Module.objects.count()
        
        # Teacher Management Search and List
        search_query = request.GET.get('q', '')
        trainers = CustomUser.objects.filter(role=CustomUser.Role.TEACHER).order_by('first_name', 'last_name')
        if search_query:
            trainers = trainers.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        context['trainers'] = trainers
        context['search_query'] = search_query
        
        from django.utils import timezone
        today = timezone.localdate()
        recent_sessions = SessionPlan.objects.all().select_related('teacher').filter(
            created_at__date=today,
            term=active_term
        ).order_by('-created_at')
        # Attach presentation attributes
        for s in recent_sessions:
            s.s_topic = s.topic
            s.s_teacher = s.teacher.username
            s.s_type = s.template_type
            s.s_date = s.created_at.strftime("%b %d")
        context['recent_sessions'] = recent_sessions
        context['active_term'] = active_term

        # 1. Performance Trends: Average score per module
        marks_qs = StudentMark.objects.filter(assessment__academic_year=active_year)
        if active_term != 'Term 3':
            marks_qs = marks_qs.filter(assessment__term=active_term)
            
        module_performance = marks_qs.values('assessment__module__module_name')\
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
        from django.utils import timezone
        today = timezone.localdate()
        sessions = SessionPlan.objects.filter(
            teacher=user,
            created_at__date=today,
            term=active_term
        ).order_by('-created_at')
        for s in sessions:
            s.stype = s.template_type
            s.stopic = s.topic
            s.sdate = s.created_at.strftime("%b %d")
        context['my_sessions'] = sessions
        context['active_term'] = active_term
        context['today'] = today
        
        classrooms = Classroom.objects.filter(Q(teacher=user) | Q(co_teachers=user)).distinct()
        total_students = 0
        for c in classrooms:
            c.cname = c.name
            c.scount = c.students.count()
            c.mcount = c.modules.count()
            c.is_owner = (c.teacher == user)
            total_students += c.scount
        context['my_classrooms'] = classrooms
        context['total_students'] = total_students

        # Metrics Calculations
        # 1. Avg Attendance
        all_attendance = Attendance.objects.filter(
            teacher=user,
            academic_year=active_year
        ).distinct()
        if active_term != 'Term 3':
            all_attendance = all_attendance.filter(term=active_term)
        total_att = all_attendance.count()
        present_att = all_attendance.filter(status__in=['PRESENT', 'LATE']).count()
        context['avg_attendance'] = round((present_att / total_att * 100), 1) if total_att > 0 else 0

        # Gender Breakdown for Overview
        teacher_students = StudentProfile.objects.filter(
            Q(classroom__teacher=user) | Q(classroom__co_teachers=user)
        ).distinct().order_by('user__first_name', 'user__last_name')
        context['total_boys'] = teacher_students.filter(sex='Male').count()
        context['total_girls'] = teacher_students.filter(sex='Female').count()

        # 2. Avg Score
        marks_qs = StudentMark.objects.filter(
            assessment__module__teacher=user,
            assessment__academic_year=active_year
        ).distinct()
        if active_term != 'Term 3':
            marks_qs = marks_qs.filter(assessment__term=active_term)
        avg_score = marks_qs.aggregate(Avg('score'), Avg('total_marks'))
        if avg_score['score__avg'] and avg_score['total_marks__avg']:
            context['avg_score'] = round((avg_score['score__avg'] / avg_score['total_marks__avg'] * 100), 1)
        else:
            context['avg_score'] = 0

        # School Peers & Share Requests
        if user.school_name:
            school_peers = CustomUser.objects.filter(
                role=CustomUser.Role.TEACHER,
                school_name__iexact=user.school_name
            ).exclude(id=user.id)
            peer_classrooms = []
            for peer in school_peers:
                for cls in peer.classrooms.all():
                    already_co = cls.co_teachers.filter(id=user.id).exists()
                    pending_req = ClassroomShareRequest.objects.filter(
                        classroom=cls, requester=user, status='PENDING'
                    ).exists()
                    peer_classrooms.append({
                        'id': cls.id,
                        'name': cls.name,
                        'owner': peer.get_full_name() or peer.username,
                        'already_co': already_co,
                        'pending': pending_req,
                    })
            context['peer_classrooms'] = peer_classrooms
        else:
            context['peer_classrooms'] = []

        # Incoming share requests (as classroom owner)
        context['incoming_requests'] = ClassroomShareRequest.objects.filter(
            receiver=user, status='PENDING'
        ).select_related('requester', 'classroom')

        return render(request, 'dashboard_teacher.html', context)
    elif user.role == CustomUser.Role.STUDENT:
        marks_qs = StudentMark.objects.filter(student=user, assessment__academic_year=active_year)
        if active_term != 'Term 3':
            marks_qs = marks_qs.filter(assessment__term=active_term)
        marks = marks_qs.order_by('-date_recorded')[:10]
        # Attach presentation attributes to marks
        for m in marks:
            m.status_label = "Completed"
            m.status_class = "bg-emerald-50 text-emerald-600 border border-emerald-100"
            m.m_max = m.total_max if hasattr(m, 'total_max') and m.total_max else (m.assessment.total_marks if m.assessment else 100)
            m.m_name = m.assessment.module_name if m.assessment and hasattr(m.assessment, 'module_name') and m.assessment.module_name else "CORE MODULE"
        # Announcements for student's classroom
        from .models import Announcement, SessionPlan
        classroom = user.student_profile.classroom if hasattr(user, 'student_profile') else None
        if classroom:
            context['announcements'] = Announcement.objects.filter(classroom=classroom)[:5]
        else:
            context['announcements'] = []

        # Strictly filter session plans based on class level (Level 3 sees level 3, Level 4 sees level 4, etc.)
        student_level_str = getattr(user.student_profile, 'level', '')
        student_level_digit = None
        for char in student_level_str:
            if char.isdigit():
                student_level_digit = char
                break
        if not student_level_digit and classroom:
            for char in classroom.name:
                if char.isdigit():
                    student_level_digit = char
                    break

        all_plans_qs = SessionPlan.objects.all().order_by('-created_at')
        session_plans = []
        for plan in all_plans_qs:
            plan_level_str = getattr(plan, 'level', '')
            plan_digit = None
            for char in plan_level_str:
                if char.isdigit():
                    plan_digit = char
                    break
            
            # If both have digit designations, enforce a strict match
            if student_level_digit and plan_digit:
                if student_level_digit == plan_digit:
                    session_plans.append(plan)
            # If no levels are set for the student, fall back to showing all
            elif not student_level_digit:
                session_plans.append(plan)

        context['session_plans'] = session_plans[:6]
        context['marks'] = marks
        context['ufirst'] = user.username[0].upper() if user.username else "U"
        context['sid'] = user.student_profile.student_id if hasattr(user, 'student_profile') and user.student_profile and user.student_profile.student_id else "STU-2026-X"

        # Profile completion
        profile = getattr(user, 'student_profile', None)
        completion_items = [
            {'label': 'Email address', 'done': bool(user.email), 'url': 'edit_profile'},
            {'label': 'Profile photo', 'done': bool(profile and profile.profile_picture), 'url': 'edit_profile'},
            {'label': 'Bio / About me', 'done': bool(profile and profile.bio and profile.bio.strip()), 'url': 'edit_profile'},
        ]
        done_count = sum(1 for i in completion_items if i['done'])
        context['profile_completion_pct'] = int(done_count / len(completion_items) * 100)
        context['profile_completion_items'] = completion_items
        context['profile_completion_done'] = done_count
        context['profile_completion_total'] = len(completion_items)

        return render(request, 'dashboard_student.html', context)

@login_required
def student_session_detail_view(request, session_id):
    if request.user.role != CustomUser.Role.STUDENT:
        messages.error(request, "Access restricted to students.")
        return redirect('dashboard')
        
    session = get_object_or_404(SessionPlan, id=session_id)
    student = request.user
    classroom = getattr(student.student_profile, 'classroom', None)
    
    # Enforce Class Level Security Authorization
    student_level_str = getattr(student.student_profile, 'level', '')
    student_level_digit = None
    for char in student_level_str:
        if char.isdigit():
            student_level_digit = char
            break
    if not student_level_digit and classroom:
        for char in classroom.name:
            if char.isdigit():
                student_level_digit = char
                break
                
    plan_level_str = getattr(session, 'level', '')
    plan_digit = None
    for char in plan_level_str:
        if char.isdigit():
            plan_digit = char
            break
            
    if student_level_digit and plan_digit and student_level_digit != plan_digit:
        messages.error(request, "You are not authorized to view session plans for another class level.")
        return redirect('dashboard')

    # ── Collect marks across ALL terms and ALL academic years ──────────────────
    # We use two strategies and merge:
    #   1. Direct FK link: assessment.session == this session plan
    #   2. Module name / code fuzzy or keyword match against session text fields
    from .models import StudentMark
    s_mod = session.module.lower().strip() if session.module else ''

    # Strategy 1 – direct session link
    direct_qs = StudentMark.objects.filter(
        student=student,
        assessment__session=session
    ).select_related('assessment__module', 'assessment__academic_year')

    # Strategy 2 – module name/code match (all terms, all years)
    all_student_marks = StudentMark.objects.filter(
        student=student,
        assessment__module__isnull=False
    ).select_related('assessment__module', 'assessment__academic_year')

    seen_ids = set()
    combined = []
    for mark in list(direct_qs):
        if mark.id not in seen_ids:
            seen_ids.add(mark.id)
            combined.append(mark)

    # Pre-compile the session text fields for broader keyword matching if direct fields don't match
    session_text = " ".join([
        session.module or '',
        session.topic or '',
        session.objectives or '',
        session.learning_outcome or '',
        session.indicative_content or '',
        session.performance_criteria or '',
        session.trade or '',
    ]).lower()

    for mark in all_student_marks:
        if mark.id in seen_ids:
            continue
        if mark.assessment and mark.assessment.module:
            m_code = mark.assessment.module.module_code.lower().strip()
            m_name = mark.assessment.module.module_name.lower().strip()
            
            # Check 1: Fuzzy/substring match using session's module field (if present)
            matched = False
            if s_mod and (m_code in s_mod or m_name in s_mod or s_mod in m_code or s_mod in m_name):
                matched = True
            
            # Check 2: Broader search in session plan text if not already matched
            if not matched:
                if m_code in session_text or m_name in session_text:
                    matched = True
                else:
                    # Check 3: Word overlap for multi-word modules (e.g. "Develop Website" vs "Website Development")
                    ignore_words = {'and', 'or', 'of', 'using', 'apply', 'develop', 'the', 'for', 'with', 'in', 'to', 'a', 'an'}
                    m_words = [w for w in m_name.replace("  ", " ").split() if w not in ignore_words and len(w) > 2]
                    if m_words and all(w in session_text for w in m_words):
                        matched = True
            
            if matched:
                seen_ids.add(mark.id)
                combined.append(mark)

    # Build rich breakdown list for template
    marks_breakdown = []
    for mark in combined:
        total = mark.total_marks if mark.total_marks else 100
        pct = round((mark.score / total) * 100, 1) if total > 0 else 0
        colour = 'emerald' if pct >= 80 else ('amber' if pct >= 60 else 'rose')
        marks_breakdown.append({
            'title':    mark.assessment.title if mark.assessment else 'Assessment',
            'atype':    mark.assessment.get_assessment_type_display() if mark.assessment else '',
            'term':     getattr(mark.assessment, 'term', '') or '',
            'year':     str(mark.assessment.academic_year) if mark.assessment and mark.assessment.academic_year else '',
            'score':    mark.score,
            'total':    total,
            'pct':      pct,
            'colour':   colour,
        })

    # Sort by year then term then assessment title for a clean chronological view
    term_order = {'Term 1': 0, 'Term 2': 1, 'Term 3': 2}
    marks_breakdown.sort(key=lambda x: (x['year'], term_order.get(x['term'], 9), x['title']))

    # Combined overall percentage across all collected marks
    if marks_breakdown:
        total_score = sum(m['score'] for m in marks_breakdown)
        total_max   = sum(m['total'] for m in marks_breakdown)
        score_pct   = round((total_score / total_max) * 100, 1) if total_max > 0 else 0
        has_marks   = True
    else:
        score_pct = 0.0
        has_marks = False

    context = {
        'session':        session,
        'score_pct':      score_pct,
        'has_marks':      has_marks,
        'marks_breakdown': marks_breakdown,
    }
    return render(request, 'student_session_detail.html', context)


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
        # Sanitize filename to prevent newlines/quotes in HTTP header
        clean_topic = session.topic.replace('\n', ' ').replace('\r', '').replace('"', '').replace("'", "").strip()
        if len(clean_topic) > 100:
            clean_topic = clean_topic[:97] + "..."
        response['Content-Disposition'] = f'inline; filename="{clean_topic}.pdf"'
        return response
    else:
        return HttpResponse("WeasyPrint not installed or configured.", status=500)



@login_required
def generate_advanced_session_plan_view(request):
    from .utils import generate_advanced_session_plan_ai
    from .models import SessionPlan, Activity, Trade, Curriculum, SyllabusModule, LearningOutcome, IndicativeContent, Topic
    
    if request.user.role == CustomUser.Role.ADMIN:
        trades = Trade.objects.all()
    else:
        trades = request.user.trades.all()
        
    if request.method == 'POST':
        # Now we read from the cascaded dropdowns instead of manual text
        trade_id = request.POST.get('trade_id', '')
        curriculum_id = request.POST.get('curriculum_id', '')
        module_id = request.POST.get('module_id', '')
        lo_id = request.POST.get('lo_id', '')
        ic_id = request.POST.get('ic_id', '')
        topic_ids = request.POST.getlist('topics') # Checkboxes
        
        template_type = request.POST.get('template_type', 'THEORY')
        
        # Build strict context from DB models
        syllabus_text = ""
        range_text = ""
        trade_name = ""
        
        if trade_id:
            trade = Trade.objects.filter(id=trade_id).first()
            trade_name = trade.name if trade else ""
            
        if module_id:
            mod = SyllabusModule.objects.filter(id=module_id).first()
            if mod: syllabus_text += f"Module: {mod.code} - {mod.title}\n"
            
        if lo_id:
            lo = LearningOutcome.objects.filter(id=lo_id).first()
            if lo: syllabus_text += f"Learning Outcome: {lo.title}\n"
            
        if ic_id:
            ic = IndicativeContent.objects.filter(id=ic_id).first()
            if ic: syllabus_text += f"Indicative Content: {ic.title}\n"
            
        if topic_ids:
            selected_topics = Topic.objects.filter(id__in=topic_ids)
            topics_str = "\n".join([f"{i+1}. {t.title}" for i, t in enumerate(selected_topics)])
            range_text = topics_str
            syllabus_text += f"Selected Topics to Cover:\n{topics_str}\n"
            
        # Fallbacks to the old form inputs if people didn't use the cascade
        if not syllabus_text:
            syllabus_text = request.POST.get('syllabus_text', '')
        if not range_text:
            range_text = request.POST.get('range_text', '')
            
        extra_data = {
            'sector': request.POST.get('sector', ''),
            'trade': trade_name or request.POST.get('trade', ''),
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
            plan_data = generate_advanced_session_plan_ai(syllabus_text, range_text, template_type, user=request.user, **extra_data)
            
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
                module=f"{mod.code} - {mod.title}" if (module_id and mod) else plan_data['module'],
                learning_outcome=lo.title if (lo_id and lo) else plan_data['learning_outcome'],
                indicative_content=ic.title if (ic_id and ic) else plan_data.get('indicative_content', ''),
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
                reflection=plan_data.get('reflection', ''),
                references=plan_data.get('references', ''),
                slow_learners_strategy=plan_data.get('slow_learners_strategy', ''),
                advanced_learners_strategy=plan_data.get('advanced_learners_strategy', ''),
                inclusivity_strategy=plan_data.get('inclusivity_strategy', ''),
                student_summary=plan_data.get('student_summary', '')
            )
            
            for act in plan_data['activities']:
                Activity.objects.create(
                    session=session,
                    step_name=act['step_name'],
                    trainer_activity=act['trainer'],
                    learner_activity=act['learner'],
                    time_allocation=act['time']
                )
            
            messages.success(request, f"Advanced session plan for '{plan_data['topic'][:50]}...' generated successfully! Tweak it below before printing.")
            return redirect('edit_session_plan', session_id=session.id)
            
    # Pass current term and classrooms list to context
    from .models import Classroom
    classrooms = Classroom.objects.all().order_by('name')
    active_term = SystemSetting.get_settings().current_term
    return render(request, 'generate_advanced_session_plan.html', {
        'trades': trades, 
        'current_term': active_term,
        'classrooms': classrooms
    })

@login_required
def edit_session_plan_view(request, session_id):
    session = get_object_or_404(SessionPlan, id=session_id)
    
    # Check permissions (must be creator or admin)
    if not request.user.is_superuser and request.user.role != CustomUser.Role.ADMIN and session.teacher != request.user:
        messages.error(request, "You do not have permission to edit this session plan.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        # Retrieve form data
        session.sector = request.POST.get('sector', '')
        session.trade = request.POST.get('trade', '')
        session.level = request.POST.get('level', '')
        session.class_name = request.POST.get('class_name', '')
        session.num_students = int(request.POST.get('num_students', 0) or 0)
        session.academic_year = request.POST.get('academic_year', '')
        session.term = request.POST.get('term', '')
        session.weeks = request.POST.get('weeks', '')
        session.module = request.POST.get('module', '')
        session.learning_outcome = request.POST.get('learning_outcome', '')
        session.indicative_content = request.POST.get('indicative_content', '')
        session.performance_criteria = request.POST.get('performance_criteria', '')
        session.pre_requisite_knowledge = request.POST.get('pre_requisite_knowledge', '')
        session.topic = request.POST.get('topic', '')
        session.range_details = request.POST.get('range_details', '')
        session.duration = request.POST.get('duration', '')
        session.facilitation_technique = request.POST.get('facilitation_technique', '')
        
        # Quill / WYSIWYG rich text fields
        session.objectives = request.POST.get('objectives', '')
        session.cross_cutting_issues = request.POST.get('cross_cutting_issues', '')
        session.hse_considerations = request.POST.get('hse_considerations', '')
        session.ict_tools = request.POST.get('ict_tools', '')
        session.special_needs_support = request.POST.get('special_needs_support', '')
        session.resources = request.POST.get('resources', '')
        session.reflection = request.POST.get('reflection', '')
        session.references = request.POST.get('references', '')
        session.slow_learners_strategy = request.POST.get('slow_learners_strategy', '')
        session.advanced_learners_strategy = request.POST.get('advanced_learners_strategy', '')
        session.inclusivity_strategy = request.POST.get('inclusivity_strategy', '')
        session.student_summary = request.POST.get('student_summary', '')
        
        session.save()
        
        # Dynamic Activities / Steps Table
        # Delete old activities and re-create them to allow full inserts/deletes/re-ordering
        session.activities.all().delete()
        
        step_names = request.POST.getlist('step_name[]')
        trainer_activities = request.POST.getlist('trainer_activity[]')
        learner_activities = request.POST.getlist('learner_activity[]')
        time_allocations = request.POST.getlist('time_allocation[]')
        resources_needed_list = request.POST.getlist('resources_needed[]')
        
        for i in range(len(step_names)):
            if step_names[i].strip():
                Activity.objects.create(
                    session=session,
                    step_name=step_names[i],
                    trainer_activity=trainer_activities[i] if i < len(trainer_activities) else '',
                    learner_activity=learner_activities[i] if i < len(learner_activities) else '',
                    time_allocation=time_allocations[i] if i < len(time_allocations) else '',
                    resources_needed=resources_needed_list[i] if i < len(resources_needed_list) else ''
                )
                
        messages.success(request, "Session plan changes saved successfully!")
        
        if 'export_pdf' in request.POST:
            return redirect('view_session_pdf', session_id=session.id)
            
        return redirect('dashboard')
        
    return render(request, 'edit_session_plan.html', {'session': session})

@login_required
def session_plans_list_view(request):
    from .models import SessionPlan
    user = request.user
    
    # Simple search
    q = request.GET.get('q', '').strip()
    
    if user.role == CustomUser.Role.TEACHER:
        sessions_qs = SessionPlan.objects.filter(teacher=user)
    elif user.role == CustomUser.Role.ADMIN:
        sessions_qs = SessionPlan.objects.all().select_related('teacher')
    else:
        return redirect('dashboard')
        
    if q:
        sessions_qs = sessions_qs.filter(topic__icontains=q)
        
    sessions = sessions_qs.order_by('-created_at')
    
    for s in sessions:
        s.stype = s.template_type
        s.stopic = s.topic
        s.sdate = s.created_at.strftime("%b %d, %Y")
        s.s_teacher = s.teacher.get_full_name() or s.teacher.username
        
    return render(request, 'session_plans_list.html', {
        'sessions': sessions,
        'q': q
    })

@login_required
def create_assessment_view(request):
    from .forms import AssessmentForm
    if request.method == 'POST':
        form = AssessmentForm(request.user, request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            active_year, active_term = _get_active_timeline(request)
            assessment.academic_year = active_year
            assessment.term = active_term
            assessment.save()
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
    students = classroom.students.all().order_by('user__first_name', 'user__last_name') # StudentProfile objects
    
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
            from .notifications import send_marks_email
            for mark in marks:
                if mark.score > assessment.total_marks:
                    mark.score = assessment.total_marks
                mark.save()
                
                # Create Notification for student
                Notification.objects.create(
                    user=mark.student,
                    message=f"New marks entered for {assessment.title}: {mark.score}/{assessment.total_marks}",
                    notification_type=Notification.NotificationType.INFO
                )
                
                # Send email notification
                send_marks_email(mark, assessment)
                
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
    
    classrooms = Classroom.objects.filter(Q(teacher=request.user) | Q(co_teachers=request.user)).distinct()
    return render(request, 'select_attendance_class.html', {'classrooms': classrooms})

@login_required
def perform_attendance_view(request, class_id):
    from .models import StudentProfile, Attendance, Classroom
    import datetime
    
    classroom = get_object_or_404(Classroom, id=class_id)
    if classroom.teacher != request.user and request.user not in classroom.co_teachers.all():
        return redirect('dashboard')
    date_str = request.GET.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    active_year, active_term = _get_active_timeline(request)
    
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
                                'classroom': classroom,
                                'academic_year': active_year,
                                'term': active_term
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
    attendance_records = Attendance.objects.filter(classroom=classroom, date=date_str, academic_year=active_year)
    attendance_dict = {record.student_id: record.status for record in attendance_records}

    # Pre-calculate student info
    profiles = classroom.students.all().select_related('user').order_by('user__first_name', 'user__last_name')
    students_data = []
    for p in profiles:
        students_data.append({
            'id': p.user.id,
            'sid': p.student_id or "N/A",
            'name': p.user.get_full_name() or p.user.username,
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
    classroom = get_object_or_404(Classroom, id=class_id)
    is_owner = classroom.teacher == request.user
    is_co_teacher = request.user in classroom.co_teachers.all()
    if not is_owner and not is_co_teacher:
        return redirect('dashboard')
    # Only show modules owned by the current teacher
    modules = classroom.modules.filter(teacher=request.user)
    # Pre-calculate student data to avoid template logic breakage
    profiles = classroom.students.all().select_related('user').order_by('user__first_name', 'user__last_name')
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
    
    # Fetch all assessments for this teacher's modules
    active_year, active_term = _get_active_timeline(request)
    assessments = Assessment.objects.filter(module__classroom=classroom, academic_year=active_year, module__teacher=request.user).select_related('module').order_by('-created_at')
    if active_term != 'Term 3':
        assessments = assessments.filter(term=active_term)
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
    
    # Calculate Avg Attendance for this teacher's records
    class_att = Attendance.objects.filter(classroom=classroom, academic_year=active_year, teacher=request.user)
    if active_term != 'Term 3':
        class_att = class_att.filter(term=active_term)
    total_class_att = class_att.count()
    present_class_att = class_att.filter(status__in=['PRESENT', 'LATE']).count()
    class_avg_attendance = round((present_class_att / total_class_att * 100), 1) if total_class_att > 0 else 0

    # Gender Breakdown for Class
    boys_count = profiles.filter(sex='Male').count()
    girls_count = profiles.filter(sex='Female').count()
    
    # School peers eligible to be added as co-teachers (owner only, same school, not already co-teacher)
    school_peers_for_invite = []
    if is_owner and request.user.school_name:
        school_peers_for_invite = CustomUser.objects.filter(
            role=CustomUser.Role.TEACHER,
            school_name__iexact=request.user.school_name
        ).exclude(id=request.user.id).exclude(id__in=classroom.co_teachers.values_list('id', flat=True))

    return render(request, 'manage_class.html', {
        'classroom': classroom,
        'modules': modules,
        'students': students_list,
        'assessments': assessments_data,
        'avg_attendance': class_avg_attendance,
        'boys_count': boys_count,
        'girls_count': girls_count,
        'is_owner': is_owner,
        'co_teachers': classroom.co_teachers.all(),
        'school_peers_for_invite': school_peers_for_invite,
    })

@login_required
def student_report_view(request, student_id):
    from .models import CustomUser, StudentMark, Attendance
    from collections import defaultdict
    
    student = get_object_or_404(CustomUser, id=student_id)
    # Security: Teacher must own the class or Student must be the user
    if request.user.role == CustomUser.Role.STUDENT and request.user.id != student_id:
        return redirect('dashboard')
    
    # Marks logic
    active_year, active_term = _get_active_timeline(request)
    marks = StudentMark.objects.filter(student=student, assessment__academic_year=active_year).select_related('assessment__module').order_by('assessment__module')
    if active_term != 'Term 3':
        marks = marks.filter(assessment__term=active_term)
    
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
    att_qs = Attendance.objects.filter(student=student, academic_year=active_year)
    if active_term != 'Term 3':
        att_qs = att_qs.filter(term=active_term)
    total_attendance = att_qs.count()
    present_attendance = att_qs.filter(status__in=['PRESENT', 'LATE']).count()
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
    
    active_year, active_term = _get_active_timeline(request)
    marks = StudentMark.objects.filter(student=student, assessment__academic_year=active_year).select_related('assessment__module')
    if active_term != 'Term 3':
        marks = marks.filter(assessment__term=active_term)
    
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
        student.save()
        
        # Create student profile
        profile = StudentProfile.objects.create(
            user=student,
            classroom=classroom,
            sex=sex
        )
        
        AuditLog.objects.create(
            user=request.user,
            action="Added Student",
            details=f"Added {student.get_full_name()} to class {classroom.name}"
        )
        
        messages.success(request, f"Student '{student.get_full_name() or username}' added successfully. Default password: student123")
        return redirect('manage_class', class_id=class_id)
    
    return render(request, 'add_student.html', {'classroom': classroom})

@login_required
def add_module_view(request, class_id):
    from .models import Classroom, Module
    classroom = get_object_or_404(Classroom, id=class_id)
    if classroom.teacher != request.user and request.user not in classroom.co_teachers.all():
        return redirect('dashboard')

    if request.method == 'POST':
        module_code = request.POST.get('module_code')
        module_name = request.POST.get('module_name')
        
        # Check if module with same code already exists for this classroom
        if Module.objects.filter(classroom=classroom, module_code=module_code).exists():
            messages.error(request, f"Module with code '{module_code}' already exists in this classroom.")
            return redirect('manage_class', class_id=class_id)
        
        # Create the module
        module = Module.objects.create(
            classroom=classroom,
            module_code=module_code,
            module_name=module_name,
            teacher=request.user
        )
        
        AuditLog.objects.create(
            user=request.user,
            action="Added Module",
            details=f"Added module {module_code} to class {classroom.name}"
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
                questions_json=quiz_data
            )
            assessment_id = assessment.id
            
            AuditLog.objects.create(
                user=request.user,
                action="Generated AI Quiz",
                details=f"Generated {quiz_type} quiz for module {module.module_code}"
            )
            
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
    quiz_data = assessment.questions_json if assessment.questions_json else {}
    
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
            classroom = Classroom.objects.create(
                name=class_name,
                teacher=request.user
            )
            
            AuditLog.objects.create(
                user=request.user,
                action="Created Classroom",
                details=f"Created classroom: {class_name}"
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
    
    classroom = get_object_or_404(Classroom, id=class_id)
    if classroom.teacher != request.user and request.user not in classroom.co_teachers.all():
        return redirect('dashboard')
    students = classroom.students.all().select_related('user').order_by('user__first_name', 'user__last_name')
    
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
    
    classroom = get_object_or_404(Classroom, id=class_id)
    if classroom.teacher != request.user and request.user not in classroom.co_teachers.all():
        return redirect('dashboard')
    active_year, active_term = _get_active_timeline(request)
    
    # Get all distinct dates with attendance for this class by the current teacher
    # Annotate with counts and latest time recorded
    att_qs = Attendance.objects.filter(classroom=classroom, academic_year=active_year, teacher=request.user)
    if active_term != 'Term 3':
        att_qs = att_qs.filter(term=active_term)
        
    history = att_qs.values('date').annotate(
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
    classroom = get_object_or_404(Classroom, id=class_id)
    if classroom.teacher != request.user and request.user not in classroom.co_teachers.all():
        return redirect('dashboard')
    date_str = request.POST.get('date') or request.GET.get('date')
    
    if date_str:
        Attendance.objects.filter(classroom=classroom, date=date_str, teacher=request.user).delete()
        messages.success(request, f"Attendance records for {date_str} deleted.")
    
    return redirect('manage_attendance', class_id=class_id)

@login_required
def edit_student_view(request, student_id):
    from .models import CustomUser, StudentProfile, AuditLog
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
    
    # Collect all existing distinct school names so the admin can reuse one or create new
    existing_schools = list(
        CustomUser.objects
        .filter(school_name__isnull=False)
        .exclude(school_name='')
        .values_list('school_name', flat=True)
        .distinct()
        .order_by('school_name')
    )

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
            from .notifications import send_welcome_email
            send_welcome_email(user, temp_password=form.cleaned_data.get('password'))
            messages.success(request, f"Teacher account for '{user.get_full_name() or user.username}' created successfully!")
            return redirect('dashboard')
    else:
        form = TrainerCreationForm()
    
    return render(request, 'create_trainer.html', {'form': form, 'existing_schools': existing_schools})

def privacy_policy_view(request):
    return render(request, 'privacy_policy.html')

def terms_of_service_view(request):
    return render(request, 'terms_of_service.html')

def teacher_persona_view(request):
    """High-fidelity Teacher User Persona & Navigation Guide."""
    return render(request, 'teacher_persona.html')

def student_persona_view(request):
    """High-fidelity Student User Persona & Navigation Guide."""
    return render(request, 'student_persona.html')

@login_required
def admin_persona_view(request):
    """High-fidelity Admin User Persona & Navigation Guide."""
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Only administrators can access the admin workspace guide.")
    return render(request, 'admin_persona.html')


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
    from .models import Trade
    all_trades = Trade.objects.all()
    
    if request.method == 'POST':
        trainer.username = request.POST.get('username')
        trainer.first_name = request.POST.get('first_name')
        trainer.last_name = request.POST.get('last_name')
        trainer.email = request.POST.get('email')
        trainer.school_name = request.POST.get('school_name', '').strip()
        
        # Update trades
        trade_ids = request.POST.getlist('trades')
        trainer.trades.set(trade_ids)
        
        trainer.save()
        from .models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action="Updated Trainer",
            details=f"Updated trainer details for {trainer.username} (ID: {user_id})"
        )
        return redirect('dashboard')
        
    return render(request, 'edit_trainer.html', {
        'trainer': trainer,
        'all_trades': all_trades,
        'assigned_trade_ids': list(trainer.trades.values_list('id', flat=True))
    })

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
            from .notifications import send_announcement_emails
            send_announcement_emails(announcement)
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
    classroom = get_object_or_404(Classroom, id=class_id)
    if classroom.teacher != request.user and request.user not in classroom.co_teachers.all():
        return redirect('dashboard')
    students = StudentProfile.objects.filter(classroom=classroom).order_by('user__first_name', 'user__last_name')
    # Teachers (both primary and co-teachers) only see their own modules in the gradebook
    modules = Module.objects.filter(classroom=classroom, teacher=request.user)
    
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
    from .models import StudentProfile, Module, Assessment, StudentMark, AuditLog, Classroom
    from django.contrib import messages
    from django.http import HttpResponse

    # Template Download Logic
    if request.method == 'GET' and 'download_template' in request.GET:
        try:
            classroom_id = request.GET.get('classroom')
            module_id = request.GET.get('module')
            assessment_title = request.GET.get('assessment_title', 'Final Exam')
            assessment_type = request.GET.get('assessment_type', 'FA')
            total_marks = request.GET.get('total_marks', '100')

            classroom = Classroom.objects.get(id=classroom_id)
            module = Module.objects.get(id=module_id)
            students = StudentProfile.objects.filter(classroom=classroom).select_related('user')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="grade_template_{classroom.name.replace(" ", "_")}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Student ID', 'Student Name', 'Module Code', 'Assessment', 'Type', 'Score', 'Total'])
            
            for student in students:
                writer.writerow([
                    student.student_id,
                    student.user.get_full_name() or student.user.username,
                    module.module_code,
                    assessment_title,
                    assessment_type,
                    '', # Empty score for teacher to fill
                    total_marks
                ])
            
            return response
        except Exception as e:
            messages.error(request, f"Template generation error: {str(e)}")
            return redirect('bulk_grade_import')

    # Upload Logic
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
                    assessment_type = row.get('Type', 'FA')
                    score = row.get('Score')
                    total = row.get('Total')

                    if not student_id or not module_code:
                        continue

                    # Clean score and total
                    if not score or str(score).strip() == '':
                        continue
                    
                    try:
                        score_val = float(score)
                        total_val = float(total) if (total and str(total).strip() != '') else 100.0
                    except (ValueError, TypeError):
                        error_count += 1
                        errors.append(f"Invalid score/total for Student {student_id}")
                        continue

                    student_profile = StudentProfile.objects.get(student_id=student_id)
                    module = Module.objects.get(module_code=module_code, classroom=student_profile.classroom)
                    
                    assessment, created = Assessment.objects.get_or_create(
                        module=module,
                        title=assessment_title if assessment_title else "Bulk Import",
                        defaults={
                            'total_marks': total_val,
                            'assessment_type': assessment_type
                        }
                    )

                    StudentMark.objects.update_or_create(
                        student=student_profile.user,
                        assessment=assessment,
                        defaults={'score': score_val, 'total_marks': assessment.total_marks}
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

    # Standard GET
    my_classrooms = Classroom.objects.filter(teacher=request.user).prefetch_related('modules')
    
    # Pre-calculate mapping for JS to avoid template logic in script
    mapping = {}
    for c in my_classrooms:
        mapping[str(c.id)] = [
            {'id': m.id, 'name': f"{m.module_code} - {m.module_name}"} 
            for m in c.modules.all()
        ]
    
    return render(request, 'bulk_import.html', {
        'classrooms': my_classrooms,
        'mapping_json': json.dumps(mapping)
    })

@login_required
def edit_profile(request):
    from .forms import StudentProfileForm
    from .models import StudentProfile
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        new_email = request.POST.get('email', '').strip()
        new_key = request.POST.get('gemini_api_key', '').strip()
        if form.is_valid():
            form.save()
            # Save email on the user account
            if new_email != request.user.email:
                request.user.email = new_email
                request.user.save(update_fields=['email'])
            # Save Gemini API key on the user account (Strategy D)
            if new_key != request.user.gemini_api_key:
                request.user.gemini_api_key = new_key
                request.user.save(update_fields=['gemini_api_key'])
            messages.success(request, "Profile updated successfully!")
            return redirect('dashboard')
    else:
        form = StudentProfileForm(instance=profile)
    
    return render(request, 'edit_profile.html', {'form': form})

@login_required
def portfolio_view(request, username=None):
    from .models import CustomUser, StudentMark, Attendance
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

    # Calculate Badges Dynamically
    # 1. Verified Learner
    is_verified = bool(profile.student_id) if profile else False
    
    # 2. Attendance Champ
    attendances = Attendance.objects.filter(student=target_user)
    total_att = attendances.count()
    present_att = attendances.filter(status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE]).count()
    att_percent = (present_att / total_att * 100) if total_att > 0 else 0
    att_unlocked = total_att >= 3 and att_percent >= 90

    # 3. Academic Elite
    marks = StudentMark.objects.filter(student=target_user)
    total_marks_count = marks.count()
    if total_marks_count > 0:
        total_pct = sum([round((m.score / m.total_marks * 100), 1) if m.total_marks > 0 else 0 for m in marks])
        avg_pct = total_pct / total_marks_count
    else:
        avg_pct = 0
    elite_unlocked = total_marks_count >= 2 and avg_pct >= 80

    # 4. Polymath (Multidisciplinary)
    distinct_modules = StudentMark.objects.filter(student=target_user).values('assessment__module').distinct().count()
    polymath_unlocked = distinct_modules >= 3

    badges = [
        {
            'id': 'verified',
            'title': 'Verified Learner',
            'subtitle': 'Identity Verified',
            'icon': 'shield',
            'unlocked': is_verified,
            'desc': 'Assigned to students with a verified institutional student ID.',
            'progress': 'Verified' if is_verified else 'Not Verified',
            'color_class': 'from-blue-500 to-indigo-600 shadow-blue-500/20 text-blue-500'
        },
        {
            'id': 'attendance',
            'title': 'Attendance Champ',
            'subtitle': 'Reliability & Presence',
            'icon': 'calendar',
            'unlocked': att_unlocked,
            'desc': 'Maintained a 90%+ attendance rate across 3+ recorded sessions.',
            'progress': f'{present_att}/{total_att} sessions ({att_percent:.0f}%)' if total_att > 0 else 'No Attendance Records',
            'color_class': 'from-emerald-500 to-teal-600 shadow-emerald-500/20 text-emerald-500'
        },
        {
            'id': 'elite',
            'title': 'Academic Elite',
            'subtitle': 'Scholastic Excellence',
            'icon': 'medal',
            'unlocked': elite_unlocked,
            'desc': 'Achieved an overall marks average of 80%+ across all assessments.',
            'progress': f'Avg: {avg_pct:.1f}% ({total_marks_count} marks)' if total_marks_count > 0 else 'No Marks Recorded',
            'color_class': 'from-amber-500 to-orange-500 shadow-amber-500/20 text-amber-500'
        },
        {
            'id': 'polymath',
            'title': 'Polymath',
            'subtitle': 'Cross-Disciplinary',
            'icon': 'sparkles',
            'unlocked': polymath_unlocked,
            'desc': 'Demonstrated competence across at least 3 distinct course modules.',
            'progress': f'{distinct_modules}/3 Modules',
            'color_class': 'from-purple-500 to-fuchsia-600 shadow-purple-500/20 text-purple-500'
        }
    ]

    return render(request, 'portfolio.html', {
        'student': target_user,
        'profile': profile,
        'top_skills': top_marks,
        'badges': badges
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
    marks = StudentMark.objects.filter(student=request.user).select_related('assessment__module')
    
    # Derive modules from the student's actual assessment marks (not classroom)
    # This ensures students without a classroom assignment still see their journey
    module_scores = {}
    for m in marks:
        if m.assessment and m.assessment.module:
            module = m.assessment.module
            percent = (m.score / m.total_marks * 100) if m.total_marks > 0 else 0
            if module.id not in module_scores:
                module_scores[module.id] = {'module': module, 'percentages': []}
            module_scores[module.id]['percentages'].append(percent)
    
    journey = []
    for mod_id, data in module_scores.items():
        best_percent = max(data['percentages'])
        status = 'Mastered' if best_percent >= 80 else 'In Progress'
        journey.append({
            'module': data['module'],
            'status': status,
            'score': round(best_percent, 1)
        })
    
    # Sort by score descending
    journey.sort(key=lambda x: x['score'], reverse=True)
        
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
    
    # Derive marks_data directly from student's own assessment records
    # This works even if the student has no classroom assigned
    marks = StudentMark.objects.filter(student=request.user).select_related('assessment__module')
    
    marks_data = {}
    for m in marks:
        if m.assessment and m.assessment.module:
            module_name = m.assessment.module.module_name
            percent = (m.score / m.total_marks * 100) if m.total_marks > 0 else 0
            if module_name not in marks_data:
                marks_data[module_name] = {'score_percent': percent}
            else:
                # Keep the best (highest) score per module
                marks_data[module_name]['score_percent'] = max(marks_data[module_name]['score_percent'], percent)
            
    if not marks_data:
        messages.warning(request, "No assessment results found yet. Complete some assessments first.")
        return redirect('dashboard')
        
    analysis = analyze_student_weakness(marks_data, user=request.user)
    
    return render(request, 'student_ai_assistant.html', {
        'marks_data': marks_data,
        'analysis': analysis
    })

@login_required
def test_ai_connection_view(request):
    from django.http import JsonResponse
    if request.user.role != CustomUser.Role.ADMIN:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    from .ai_quiz_generator import get_api_key, gemini_call_with_retry
    from google import genai

    api_key = get_api_key(user=request.user)
    if not api_key:
        return JsonResponse({
            'status': 'error',
            'message': 'No API key configured. Enter a key above and save first.'
        })

    try:
        client = genai.Client(api_key=api_key)
        response = gemini_call_with_retry(
            client,
            model='gemini-2.5-flash',
            contents="Reply with exactly: OK"
        )
        reply = response.text.strip()
        return JsonResponse({
            'status': 'success',
            'message': f'Connection successful. Gemini responded: "{reply}"'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Connection failed: {str(e)}'
        })

@login_required
def manage_user_emails(request):
    if request.user.role != CustomUser.Role.ADMIN:
        return redirect('dashboard')

    from .models import Classroom, AuditLog

    role_filter = request.GET.get('role', 'all')
    classroom_filter = request.GET.get('classroom', '')
    search_query = request.GET.get('q', '').strip()

    if request.method == 'POST':
        updated = 0
        user_ids = request.POST.getlist('user_id')
        for uid in user_ids:
            email_val = request.POST.get(f'email_{uid}', '').strip()
            try:
                u = CustomUser.objects.get(pk=uid)
                if u.email != email_val:
                    u.email = email_val
                    u.save(update_fields=['email'])
                    updated += 1
            except CustomUser.DoesNotExist:
                pass
        if updated:
            AuditLog.objects.create(
                user=request.user,
                action="Bulk Email Update",
                details=f"Updated email addresses for {updated} user(s)"
            )
            messages.success(request, f"Successfully updated {updated} email address{'es' if updated != 1 else ''}.")
        else:
            messages.info(request, "No changes were made.")
        qs = f'role={role_filter}&classroom={classroom_filter}&q={search_query}'
        return redirect(f'/manage-emails/?{qs}')

    users_qs = CustomUser.objects.exclude(is_superuser=True).order_by('role', 'last_name', 'first_name')

    if role_filter == 'teachers':
        users_qs = users_qs.filter(role=CustomUser.Role.TEACHER)
    elif role_filter == 'students':
        users_qs = users_qs.filter(role=CustomUser.Role.STUDENT)

    if classroom_filter:
        users_qs = users_qs.filter(student_profile__classroom_id=classroom_filter)

    if search_query:
        from django.db.models import Q
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    all_users = CustomUser.objects.exclude(is_superuser=True)
    total = all_users.count()
    with_email = all_users.exclude(email='').count()
    without_email = total - with_email

    classrooms = Classroom.objects.all().order_by('name')

    return render(request, 'manage_user_emails.html', {
        'users': users_qs,
        'role_filter': role_filter,
        'classroom_filter': classroom_filter,
        'search_query': search_query,
        'classrooms': classrooms,
        'stats': {'total': total, 'with_email': with_email, 'without_email': without_email},
    })

@login_required
def promote_students_view(request, class_id):
    from .models import Classroom, StudentProfile, AuditLog, Notification, SystemSetting
    from django.shortcuts import get_object_or_404
    from django.contrib import messages

    classroom = get_object_or_404(Classroom, pk=class_id)
    
    # Authorize: Only Classroom Trainer or Admin
    if request.user.role != CustomUser.Role.ADMIN and classroom.teacher != request.user:
        messages.error(request, "You are not authorized to manage promotions for this classroom.")
        return redirect('dashboard')

    students = StudentProfile.objects.filter(classroom=classroom).select_related('user').order_by('user__last_name', 'user__first_name')
    settings = SystemSetting.get_settings()
    current_term = settings.current_term

    # Determine current level of the classroom/students
    current_level = None
    if classroom.name:
        for lvl in ["Level 3", "Level 4", "Level 5"]:
            if lvl.lower() in classroom.name.lower():
                current_level = lvl
                break
    
    if not current_level and students.exists():
        for s in students:
            if s.level:
                current_level = s.level
                break
            if s.student_id and s.student_id.startswith('L'):
                code = s.student_id.split('-')[0]
                if code == 'L3':
                    current_level = "Level 3"
                elif code == 'L4':
                    current_level = "Level 4"
                elif code == 'L5':
                    current_level = "Level 5"
                if current_level:
                    break

    if not current_level:
        current_level = "Level 3"

    # Determine next level
    if current_level == "Level 3":
        next_level = "Level 4"
    elif current_level == "Level 4":
        next_level = "Level 5"
    else:
        next_level = "Graduated"

    # Query next level classrooms and current level classrooms
    next_classrooms = Classroom.objects.filter(name__icontains=next_level).order_by('name')
    same_classrooms = Classroom.objects.filter(name__icontains=current_level).order_by('name')
    all_classrooms = Classroom.objects.all().order_by('name')

    if request.method == 'POST':
        promoted_count = 0
        repeated_count = 0
        
        student_ids = request.POST.getlist('student_ids')
        for sid in student_ids:
            try:
                student = StudentProfile.objects.get(pk=sid, classroom=classroom)
                action = request.POST.get(f'action_{sid}')
                
                if action == 'promote':
                    old_level = student.level or current_level
                    student.level = next_level
                    
                    from .notifications import send_promotion_email
                    if next_level == 'Graduated':
                        student.classroom = None
                        student.save()
                        
                        # Audit Log & Notification
                        AuditLog.objects.create(
                            user=request.user,
                            action="Student Graduated",
                            details=f"Graduated student {student.user.get_full_name()} (ID: {student.student_id}) after Level 5 completion."
                        )
                        Notification.objects.create(
                            user=student.user,
                            message=f"Congratulations! You have completed Level 5 and officially graduated from the academy!",
                            notification_type='success'
                        )
                        send_promotion_email(student, 'promote', old_level, next_level)
                    else:
                        target_class_id = request.POST.get(f'classroom_{sid}')
                        target_class = get_object_or_404(Classroom, pk=target_class_id) if target_class_id else None
                        student.classroom = target_class
                        student.save()
                        
                        class_detail = f"classroom {target_class.name}" if target_class else "unassigned classroom"
                        AuditLog.objects.create(
                            user=request.user,
                            action="Student Promoted",
                            details=f"Promoted student {student.user.get_full_name()} (ID: {student.student_id}) from {old_level} to {next_level} in {class_detail}."
                        )
                        Notification.objects.create(
                            user=student.user,
                            message=f"Congratulations! You have been promoted from {old_level} to {next_level} by your trainer, {request.user.get_full_name()}!",
                            notification_type='success'
                        )
                        send_promotion_email(student, 'promote', old_level, next_level, target_class.name if target_class else None)
                    promoted_count += 1
                    
                elif action == 'repeat':
                    if not student.level:
                        student.level = current_level
                    target_class_id = request.POST.get(f'classroom_{sid}')
                    target_class = get_object_or_404(Classroom, pk=target_class_id) if target_class_id else classroom
                    student.classroom = target_class
                    student.save()
                    
                    AuditLog.objects.create(
                        user=request.user,
                        action="Student Repeated Year",
                        details=f"Registered student {student.user.get_full_name()} (ID: {student.student_id}) to repeat {student.level} in classroom {target_class.name}."
                    )
                    Notification.objects.create(
                        user=student.user,
                        message=f"You have been registered to repeat {student.level} in classroom {target_class.name} for the next academic year.",
                        notification_type='info'
                    )
                    from .notifications import send_promotion_email
                    send_promotion_email(student, 'repeat', student.level, student.level, target_class.name if target_class else classroom.name)
                    repeated_count += 1
                    
            except StudentProfile.DoesNotExist:
                pass

        if promoted_count or repeated_count:
            msg = f"Successfully processed actions: {promoted_count} promoted, {repeated_count} registered to repeat."
            messages.success(request, msg)
        else:
            messages.info(request, "No student actions were processed.")
            
        return redirect('manage_class', class_id=classroom.id)

    return render(request, 'promote_students.html', {
        'classroom': classroom,
        'students': students,
        'current_level': current_level,
        'next_level': next_level,
        'current_term': current_term,
        'next_classrooms': next_classrooms,
        'same_classrooms': same_classrooms,
        'all_classrooms': all_classrooms,
    })


@login_required
def timeline_select_view(request):
    if request.method == 'POST':
        year_id = request.POST.get('academic_year_id')
        term = request.POST.get('term')
        
        if year_id:
            if year_id == 'default':
                if 'view_year_id' in request.session:
                    del request.session['view_year_id']
            else:
                request.session['view_year_id'] = int(year_id)
                
        if term:
            if term == 'default':
                if 'view_term' in request.session:
                    del request.session['view_term']
            else:
                request.session['view_term'] = term
                
    referer = request.META.get('HTTP_REFERER', 'dashboard')
    return redirect(referer)


@login_required
def create_academic_year_view(request):
    from .models import AcademicYear, SystemSetting, AuditLog
    from django.contrib import messages
    
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Only administrators can create academic years.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Academic year name cannot be empty.")
            return redirect('admin_settings')
            
        # Check if already exists
        if AcademicYear.objects.filter(name=name).exists():
            messages.error(request, f"Academic year '{name}' already exists.")
            return redirect('admin_settings')
            
        try:
            # Create new academic year and set active
            ay = AcademicYear.objects.create(name=name, is_active=True)
            
            # Update global settings
            settings = SystemSetting.get_settings()
            settings.current_academic_year = ay
            settings.current_term = 'Term 1'
            settings.save()
            
            AuditLog.objects.create(
                user=request.user,
                action="Academic Year Created",
                details=f"Created and activated new Academic Year '{name}'. Set active term to Term 1."
            )
            
            messages.success(request, f"Successfully created and activated Academic Year '{name}'! All dashboards are now set to Term 1.")
        except Exception as e:
            messages.error(request, f"Failed to create academic year: {e}")
            
    return redirect('admin_settings')


@login_required
def upload_curriculum_view(request):
    from .models import CustomUser, Trade, Curriculum
    from .ai_curriculum_parser import parse_curriculum_pdf
    
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    trades = Trade.objects.all()
    
    if request.method == 'POST':
        trade_id = request.POST.get('trade')
        title = request.POST.get('title')
        qualification_level = request.POST.get('qualification_level', '')
        pdf_file = request.FILES.get('pdf_file')
        
        if trade_id and title and pdf_file:
            trade = get_object_or_404(Trade, id=trade_id)
            curriculum = Curriculum.objects.create(
                trade=trade,
                title=title,
                qualification_level=qualification_level,
                pdf_document=pdf_file
            )
            
            try:
                # Trigger AI Parsing
                modules_created = parse_curriculum_pdf(curriculum, user=request.user)
                messages.success(request, f"Successfully uploaded and extracted {modules_created} modules from the syllabus!")
            except Exception as e:
                import traceback
                print(f"--- AI EXTRACTION ERROR ---")
                traceback.print_exc()
                print(f"---------------------------")
                # Write to file so I can read it
                with open("extraction_error.log", "w") as f:
                    f.write(traceback.format_exc())
                messages.error(request, f"Curriculum saved, but AI extraction failed: {repr(e)}")
                
            return redirect('dashboard')
        else:
            messages.error(request, "Please provide all required fields.")
            
    return render(request, 'upload_curriculum.html', {'trades': trades})
@login_required
def get_curriculums(request, trade_id):
    from django.http import JsonResponse
    from .models import Curriculum
    curriculums = Curriculum.objects.filter(trade_id=trade_id).values('id', 'title', 'qualification_level')
    return JsonResponse(list(curriculums), safe=False)

@login_required
def get_modules(request, curriculum_id):
    from django.http import JsonResponse
    from .models import SyllabusModule
    modules = SyllabusModule.objects.filter(curriculum_id=curriculum_id).values('id', 'code', 'title')
    return JsonResponse(list(modules), safe=False)

@login_required
def get_learning_outcomes(request, module_id):
    from django.http import JsonResponse
    from .models import LearningOutcome
    los = LearningOutcome.objects.filter(module_id=module_id).values('id', 'title')
    return JsonResponse(list(los), safe=False)

@login_required
def get_indicative_contents(request, lo_id):
    from django.http import JsonResponse
    from .models import IndicativeContent
    ics = IndicativeContent.objects.filter(learning_outcome_id=lo_id).values('id', 'title')
    return JsonResponse(list(ics), safe=False)

@login_required
def get_topics(request, ic_id):
    from django.http import JsonResponse
    from .models import Topic
    topics = Topic.objects.filter(indicative_content_id=ic_id).values('id', 'title')
    return JsonResponse(list(topics), safe=False)

@login_required
def save_user_gemini_key(request):
    from django.http import JsonResponse
    import json
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        key = data.get('gemini_api_key', '').strip()
        
        test_key = data.get('test_key', False)
        if test_key and key:
            from google import genai
            from .ai_quiz_generator import gemini_call_with_retry
            try:
                client = genai.Client(api_key=key)
                response = gemini_call_with_retry(
                    client,
                    model='gemini-2.5-flash',
                    contents="Reply with exactly: OK"
                )
                reply = response.text.strip()
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Test connection failed: {str(e)}'})
        
        request.user.gemini_api_key = key
        request.user.save(update_fields=['gemini_api_key'])
        return JsonResponse({
            'success': True, 
            'message': 'API key saved and verified successfully!' if (test_key and key) else 'API key saved successfully!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def create_trade_view(request):
    from .models import CustomUser, Trade
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        sector = request.POST.get('sector', '')
        
        if name:
            Trade.objects.create(name=name, sector=sector)
            messages.success(request, f"Trade '{name}' created successfully!")
            return redirect('upload_curriculum')
        else:
            messages.error(request, "Trade name is required.")
            
    return render(request, 'create_trade.html')


@login_required
def send_share_request(request, classroom_id):
    from .models import Classroom, ClassroomShareRequest
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('dashboard')
    
    classroom = get_object_or_404(Classroom, id=classroom_id)
    # Check if they are in the same school
    if not request.user.school_name or not classroom.teacher.school_name or request.user.school_name.lower() != classroom.teacher.school_name.lower():
        messages.error(request, "You can only request access to classrooms in your own school.")
        return redirect('dashboard')
    
    if classroom.teacher == request.user:
        messages.error(request, "You are already the owner of this classroom.")
        return redirect('dashboard')
        
    if classroom.co_teachers.filter(id=request.user.id).exists():
        messages.error(request, "You are already a co-teacher in this classroom.")
        return redirect('dashboard')
        
    share_request, created = ClassroomShareRequest.objects.get_or_create(
        classroom=classroom,
        requester=request.user,
        receiver=classroom.teacher,
        defaults={'status': 'PENDING'}
    )
    if created:
        messages.success(request, f"Access request sent to {classroom.teacher.get_full_name() or classroom.teacher.username} for classroom '{classroom.name}'.")
    else:
        if share_request.status == 'PENDING':
            messages.info(request, "You already have a pending request for this classroom.")
        else:
            share_request.status = 'PENDING'
            share_request.save()
            messages.success(request, f"Access request re-sent to {classroom.teacher.get_full_name() or classroom.teacher.username} for classroom '{classroom.name}'.")
            
    return redirect('dashboard')


@login_required
def respond_share_request(request, request_id, action):
    from .models import ClassroomShareRequest
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('dashboard')
        
    share_request = get_object_or_404(ClassroomShareRequest, id=request_id, receiver=request.user)
    
    if action == 'approve':
        share_request.status = 'APPROVED'
        share_request.save()
        share_request.classroom.co_teachers.add(share_request.requester)
        messages.success(request, f"Request approved. {share_request.requester.get_full_name() or share_request.requester.username} is now a co-teacher for '{share_request.classroom.name}'.")
    elif action == 'reject':
        share_request.status = 'REJECTED'
        share_request.save()
        messages.success(request, f"Request from {share_request.requester.get_full_name() or share_request.requester.username} rejected.")
    else:
        messages.error(request, "Invalid action.")
        
    return redirect('dashboard')


@login_required
def add_co_teacher_direct(request, classroom_id, teacher_id):
    from .models import Classroom, CustomUser
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('manage_class', class_id=classroom_id)
        
    classroom = get_object_or_404(Classroom, id=classroom_id, teacher=request.user)
    teacher = get_object_or_404(CustomUser, id=teacher_id, role=CustomUser.Role.TEACHER)
    
    if not request.user.school_name or not teacher.school_name or request.user.school_name.lower() != teacher.school_name.lower():
        messages.error(request, "You can only add co-teachers from your own school.")
        return redirect('manage_class', class_id=classroom_id)
        
    classroom.co_teachers.add(teacher)
    
    from .models import ClassroomShareRequest
    ClassroomShareRequest.objects.filter(classroom=classroom, requester=teacher, status='PENDING').update(status='APPROVED')
    
    messages.success(request, f"{teacher.get_full_name() or teacher.username} has been added as a co-teacher.")
    return redirect('manage_class', class_id=classroom_id)


@login_required
def remove_co_teacher_view(request, classroom_id, teacher_id):
    from .models import Classroom, CustomUser
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('manage_class', class_id=classroom_id)
        
    classroom = get_object_or_404(Classroom, id=classroom_id, teacher=request.user)
    teacher = get_object_or_404(CustomUser, id=teacher_id, role=CustomUser.Role.TEACHER)
    
    classroom.co_teachers.remove(teacher)
    
    from .models import ClassroomShareRequest
    ClassroomShareRequest.objects.filter(classroom=classroom, requester=teacher).delete()
    
    messages.success(request, f"{teacher.get_full_name() or teacher.username} has been removed as a co-teacher.")
    return redirect('manage_class', class_id=classroom_id)


# --- SCHEME OF WORK MODULE SYSTEM VIEWS ---

@login_required
def admin_scheme_templates_view(request):
    from .models import SchemeOfWorkTemplate, CustomUser
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    templates = SchemeOfWorkTemplate.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        pdf_file = request.FILES.get('pdf_file')
        if title and pdf_file:
            SchemeOfWorkTemplate.objects.create(title=title, pdf_file=pdf_file)
            messages.success(request, "Scheme of Work Template uploaded successfully.")
            return redirect('admin_scheme_templates')
        else:
            messages.error(request, "Please provide both a title and a PDF template file.")
            
    return render(request, 'admin_scheme_templates.html', {'templates': templates})


@login_required
def delete_scheme_template_view(request, template_id):
    from .models import SchemeOfWorkTemplate, CustomUser
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    template = get_object_or_404(SchemeOfWorkTemplate, id=template_id)
    template.delete()
    messages.success(request, "Scheme of Work Template deleted successfully.")
    return redirect('admin_scheme_templates')


@login_required
def scheme_of_work_list_view(request):
    from .models import SchemeOfWork, CustomUser
    if request.user.role != CustomUser.Role.TEACHER:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    schemes = SchemeOfWork.objects.filter(teacher=request.user).order_by('-created_at')
    return render(request, 'scheme_of_work_list.html', {'schemes': schemes})


@login_required
def scheme_of_work_create_view(request):
    from .models import Trade, SchemeOfWorkTemplate, CustomUser
    if request.user.role != CustomUser.Role.TEACHER:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    trades = Trade.objects.all()
    templates = SchemeOfWorkTemplate.objects.all()
    trainer_name = request.user.get_full_name() or request.user.username
    
    from .models import SystemSetting
    settings = SystemSetting.get_settings()
    academic_year = settings.current_academic_year.name if settings.current_academic_year else ""
    term = settings.current_term or "Term 1"
    
    return render(request, 'scheme_of_work_create.html', {
        'trades': trades,
        'templates': templates,
        'trainer_name': trainer_name,
        'academic_year': academic_year,
        'term': term
    })


@login_required
def generate_scheme_of_work_ai(request):
    from google import genai
    import json
    import datetime
    from django.http import JsonResponse
    from django.urls import reverse
    from .models import SyllabusModule, SchemeOfWorkTemplate, SchemeOfWork, SchemeOfWorkWeek, CustomUser
    from .ai_quiz_generator import get_api_key
    
    if request.user.role != CustomUser.Role.TEACHER:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
        
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON body'}, status=400)
        
    module_id = data.get('module_id')
    template_id = data.get('template_id')
    school_year = data.get('school_year', '2025-2026')
    term = data.get('term', 'Term 1')
    class_name = data.get('class_name', 'L4 SOD')
    num_classes = int(data.get('num_classes', 1))
    date_str = data.get('date', '')
    trainer_name = data.get('trainer_name', '')
    
    if not module_id:
        return JsonResponse({'success': False, 'error': 'Module is required'}, status=400)
        
    module = get_object_or_404(SyllabusModule, id=module_id)
    template = None
    if template_id:
        template = get_object_or_404(SchemeOfWorkTemplate, id=template_id)
        
    # Compile detailed curriculum info
    curriculum_info = []
    los = module.learning_outcomes.all().prefetch_related('indicative_contents__topics')
    for lo in los:
        lo_info = {
            'title': lo.title,
            'indicative_contents': []
        }
        for ic in lo.indicative_contents.all():
            ic_info = {
                'title': ic.title,
                'topics': [t.title for t in ic.topics.all()]
            }
            lo_info['indicative_contents'].append(ic_info)
        curriculum_info.append(lo_info)
        
    api_key = get_api_key(user=request.user)
    if not api_key:
        return JsonResponse({'success': False, 'error': 'Gemini API key is missing. Please add it in System Settings or your Profile.'}, status=400)
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an expert TVET Academic Planner.
    Your task is to generate a comprehensive, high-fidelity Scheme of Work for the Syllabus Module described below.
    
    CRITICAL STRUCTURAL REQUIREMENTS:
    1. The Scheme of Work covers the WHOLE ACADEMIC YEAR consisting of 3 terms: "1st Term", "2nd Term", and "3rd Term".
    2. You must distribute the syllabus content and outcomes logically across these 3 terms.
    3. GRANULAR ROW LAYOUT: Every row in the "weeks" array must represent exactly ONE Indicative Content (IC) item under its parent Learning Outcome (LO).
         - DO NOT group multiple ICs into a single row. If an LO has 3 ICs, generate 3 separate rows in sequence (one for each IC), repeating the parent LO information.
    4. Schedulings: Within each term, sequence weeks logically (e.g. "1", "2", etc.).
    5. The sum of durations for all generated rows MUST EXACTLY sum to the total learning hours ({module.hours} hours). Format durations like "4hrs" or "6hrs".
    6. For the "dates" field, suggest an empty string "" or a logical placeholder range e.g. "Sep 1 - Sep 5".
    
    Syllabus Module Details:
    - Code: {module.code}
    - Title: {module.title}
    - RQF Level: {module.curriculum.qualification_level or 'IV'}
    - Trade: {module.curriculum.trade.name}
    - Sector: {module.curriculum.trade.sector or 'ICT'}
    - Total Learning Hours: {module.hours} hours
    - Credits: {module.credits}
    
    Curriculum Elements (Learning Outcomes, Indicative Content, and Topics):
    {json.dumps(curriculum_info, indent=2)}
    
    For each row entry in the `"weeks"` list, populate the following fields:
    - term: The academic term this row belongs to (exactly "1st Term", "2nd Term", or "3rd Term").
    - week_number: e.g. "1", "2", "3" (week number within that term).
    - dates: e.g. "" or a logical placeholder range like "Sep 1 - Sep 5".
    - learning_outcome: The parent Learning Outcome (LO) title/description.
    - duration: Allocated duration for this specific IC row, e.g. "4hrs" or "6hrs" (such that all rows add up to {module.hours} hours).
    - indicative_content: The specific single Indicative Content (IC) item title and topics.
    - learning_activities: Engaging, student-centered activities.
    - resources: Software, tools, equipment required.
    - formative_assessment: Assessment evidence/methods.
    - learning_place: e.g. "Computer Lab" or "Classroom".
    - observation: Any optional remarks or blank string.
    
    Output format must be strictly valid JSON ONLY, representing the structured Scheme of Work.
    
    Expected JSON Output structure:
    {{
        "sector": "...",
        "trade": "...",
        "qualification_title": "...",
        "rqf_level": "...",
        "weeks": [
            {{
                "term": "1st Term",
                "week_number": "1",
                "dates": "",
                "learning_outcome": "LO1: Develop RESTFUL APIs with Node JS",
                "duration": "4hrs",
                "indicative_content": "IC1.1: Development environment properly arranged based on coding architecture",
                "learning_activities": "Group Discussion, Practical lab exercise",
                "resources": "VS Code, Nodejs, Internet, Laptops",
                "formative_assessment": "Written assessment, Performance evaluation",
                "learning_place": "Computer Lab",
                "observation": ""
            }},
            {{
                "term": "1st Term",
                "week_number": "2",
                "dates": "",
                "learning_outcome": "LO1: Develop RESTFUL APIs with Node JS",
                "duration": "4hrs",
                "indicative_content": "IC1.2: Server and database connection setup",
                "learning_activities": "Lab demonstration, Guided practice",
                "resources": "VS Code, Nodejs, DBMS",
                "formative_assessment": "Lab assignment",
                "learning_place": "Computer Lab",
                "observation": ""
            }}
        ]
    }}
    
    Do not use markdown formatting block like ```json. Return the raw JSON text strictly.
    """
    
    try:
        from .ai_quiz_generator import gemini_call_with_retry
        response = gemini_call_with_retry(
            client,
            model='gemini-2.5-flash',
            contents=prompt
        )
        response_text = response.text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        data_json = json.loads(response_text)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"AI Generation failed: {str(e)}"}, status=500)
        
    sector = data_json.get('sector') or module.curriculum.trade.sector or 'ICT'
    trade = data_json.get('trade') or module.curriculum.trade.name
    qualification_title = data_json.get('qualification_title') or f"Certificate {module.curriculum.qualification_level or 'IV'} in {module.curriculum.trade.name}"
    rqf_level = data_json.get('rqf_level') or module.curriculum.qualification_level or 'IV'
    
    try:
        if date_str:
            date_val = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            date_val = datetime.date.today()
    except ValueError:
        date_val = datetime.date.today()
        
    scheme = SchemeOfWork.objects.create(
        teacher=request.user,
        template=template,
        syllabus_module=module,
        sector=sector,
        trade=trade,
        qualification_title=qualification_title,
        school_year=school_year,
        term=term,
        rqf_level=rqf_level,
        trainer_name=trainer_name or request.user.get_full_name() or request.user.username,
        module_code=module.code,
        module_title=module.title,
        learning_hours=module.hours,
        num_classes=num_classes,
        class_name=class_name,
        date=date_val
    )
    
    for w in data_json.get('weeks', []):
        SchemeOfWorkWeek.objects.create(
            scheme=scheme,
            term=w.get('term', '1st Term'),
            week_number=w.get('week_number', '1'),
            dates=w.get('dates', ''),
            learning_outcome=w.get('learning_outcome', ''),
            duration=w.get('duration', ''),
            indicative_content=w.get('indicative_content', ''),
            learning_activities=w.get('learning_activities', ''),
            resources=w.get('resources', ''),
            formative_assessment=w.get('formative_assessment', ''),
            learning_place=w.get('learning_place', ''),
            observation=w.get('observation', '')
        )
        
    return JsonResponse({'success': True, 'redirect_url': reverse('scheme_of_work_editor', kwargs={'scheme_id': scheme.id})})


@login_required
def scheme_of_work_editor_view(request, scheme_id):
    from .models import SchemeOfWork, CustomUser
    if request.user.role != CustomUser.Role.TEACHER:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    scheme = get_object_or_404(SchemeOfWork, id=scheme_id, teacher=request.user)
    weeks = scheme.weeks.all().order_by('id')
    return render(request, 'scheme_of_work_editor.html', {
        'scheme': scheme,
        'weeks': weeks
    })


@login_required
def scheme_of_work_save(request, scheme_id):
    import json
    import datetime
    from django.http import JsonResponse
    from .models import SchemeOfWork, SchemeOfWorkWeek, CustomUser
    
    if request.user.role != CustomUser.Role.TEACHER:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
    scheme = get_object_or_404(SchemeOfWork, id=scheme_id, teacher=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            scheme.sector = data.get('sector', scheme.sector)
            scheme.trade = data.get('trade', scheme.trade)
            scheme.qualification_title = data.get('qualification_title', scheme.qualification_title)
            scheme.school_year = data.get('school_year', scheme.school_year)
            scheme.term = data.get('term', scheme.term)
            scheme.rqf_level = data.get('rqf_level', scheme.rqf_level)
            scheme.trainer_name = data.get('trainer_name', scheme.trainer_name)
            scheme.module_code = data.get('module_code', scheme.module_code)
            scheme.module_title = data.get('module_title', scheme.module_title)
            scheme.learning_hours = int(data.get('learning_hours', scheme.learning_hours))
            scheme.num_classes = int(data.get('num_classes', scheme.num_classes))
            scheme.class_name = data.get('class_name', scheme.class_name)
            
            date_str = data.get('date')
            if date_str:
                scheme.date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                
            scheme.save()
            
            # Recreate all week entries
            SchemeOfWorkWeek.objects.filter(scheme=scheme).delete()
            for w in data.get('weeks', []):
                SchemeOfWorkWeek.objects.create(
                    scheme=scheme,
                    term=w.get('term', '1st Term'),
                    week_number=w.get('week_number', '1'),
                    dates=w.get('dates', ''),
                    learning_outcome=w.get('learning_outcome', ''),
                    duration=w.get('duration', ''),
                    indicative_content=w.get('indicative_content', ''),
                    learning_activities=w.get('learning_activities', ''),
                    resources=w.get('resources', ''),
                    formative_assessment=w.get('formative_assessment', ''),
                    learning_place=w.get('learning_place', ''),
                    observation=w.get('observation', '')
                )
                
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def delete_scheme_of_work(request, scheme_id):
    from .models import SchemeOfWork, CustomUser
    if request.user.role != CustomUser.Role.TEACHER:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    scheme = get_object_or_404(SchemeOfWork, id=scheme_id, teacher=request.user)
    scheme.delete()
    messages.success(request, "Scheme of Work deleted successfully.")
    return redirect('scheme_of_work_list')


@login_required
def scheme_of_work_pdf_view(request, scheme_id):
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from weasyprint import HTML
    from .models import SchemeOfWork, CustomUser
    
    scheme = get_object_or_404(SchemeOfWork, id=scheme_id)
    if request.user.role == CustomUser.Role.TEACHER and scheme.teacher != request.user:
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    weeks = scheme.weeks.all().order_by('id')
    
    html_string = render_to_string('scheme_of_work_pdf.html', {
        'scheme': scheme,
        'weeks': weeks,
        'request': request
    })
    
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Scheme_of_Work_{scheme.module_code}.pdf"'
    return response

