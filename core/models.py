from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
import random
import datetime

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", _("Admin")
        TEACHER = "TEACHER", _("Teacher")
        STUDENT = "STUDENT", _("Student")

    role = models.CharField(max_length=50, choices=Role.choices, default=Role.STUDENT)
    school_name = models.CharField(max_length=150, blank=True, null=True, help_text="The school/institution name this user belongs to")
    trades = models.ManyToManyField('Trade', related_name='teachers', blank=True, help_text="Trades this teacher is qualified to teach")

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

class Classroom(models.Model):
    name = models.CharField(max_length=100) # e.g., "Level 4 Software"
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.TEACHER}, related_name='classrooms')
    co_teachers = models.ManyToManyField(CustomUser, related_name='co_taught_classrooms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ClassroomShareRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='share_requests')
    requester = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_share_requests')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_share_requests')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('classroom', 'requester')

    def __str__(self):
        return f"{self.requester.username} request for {self.classroom.name} ({self.status})"


class Module(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='modules')
    module_code = models.CharField(max_length=20) # e.g. "M01"
    module_name = models.CharField(max_length=100)
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.TEACHER}, related_name='modules')

    def __str__(self):
        return f"{self.module_code} - {self.module_name}"

class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True, blank=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    level = models.CharField(max_length=50, blank=True)
    sex = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def generate_student_id(self):
        # Logic: L{Level}-YEAR-RANDOM (e.g., L4-2026-4821)
        lvl_code = "Gen"
        if self.classroom and "Level" in self.classroom.name:
             parts = self.classroom.name.split()
             for part in parts:
                 if part.isdigit():
                     lvl_code = f"L{part}"
                     break
        
        year = datetime.date.today().year
        rand_num = random.randint(1000, 9999)
        return f"{lvl_code}-{year}-{rand_num}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = self.generate_student_id()
            while StudentProfile.objects.filter(student_id=self.student_id).exists():
                 self.student_id = self.generate_student_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.student_id})"

class Resource(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.module.module_code})"

class SessionPlan(models.Model):
    class TemplateType(models.TextChoices):
        THEORY = "THEORY", _("Delivering (Theory)")
        PRACTICAL = "PRACTICAL", _("Practical")

    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.TEACHER})
    trainer_name = models.CharField(max_length=100, blank=True)
    template_type = models.CharField(max_length=20, choices=TemplateType.choices, default=TemplateType.THEORY)
    
    # Common Fields
    sector = models.CharField(max_length=100)
    trade = models.TextField()
    level = models.CharField(max_length=50, blank=True)
    class_name = models.CharField(max_length=100, blank=True)
    num_students = models.IntegerField(null=True, blank=True)
    academic_year = models.CharField(max_length=50, blank=True)
    term = models.CharField(max_length=50, blank=True)
    weeks = models.CharField(max_length=50, blank=True)
    module = models.TextField() # e.g., Software Development
    learning_outcome = models.TextField()
    indicative_content = models.TextField(blank=True)
    performance_criteria = models.TextField(blank=True, help_text="Specific performance criteria from RTB curriculum")
    pre_requisite_knowledge = models.TextField(blank=True, help_text="Link to previous lessons or required prior knowledge")
    cross_cutting_issues = models.TextField(blank=True, help_text="Gender, Environment, Inclusive education, etc.")
    hse_considerations = models.TextField(blank=True, help_text="Health, Safety, and Environment considerations")
    ict_tools = models.TextField(blank=True, help_text="ICT tools used for facilitation")
    special_needs_support = models.TextField(blank=True, help_text="Support for students with special educational needs")
    
    # Specific Fields
    topic = models.TextField()
    objectives = models.TextField()
    facilitation_technique = models.CharField(max_length=100, blank=True) # e.g. Jig-saw
    resources = models.TextField(blank=True)
    
    # Practical specific
    range_details = models.TextField(blank=True, help_text="Range of variables")
    duration = models.CharField(max_length=50, blank=True) # e.g. "2 Hours"
    reflection = models.TextField(blank=True)
    references = models.TextField(blank=True, help_text="References and citations")
    
    # Differentiated Learning & Inclusivity Strategies
    slow_learners_strategy = models.TextField(blank=True, help_text="Strategy for slow learners")
    advanced_learners_strategy = models.TextField(blank=True, help_text="Strategy for advanced learners")
    inclusivity_strategy = models.TextField(blank=True, help_text="Strategy for inclusivity/accommodations")
    student_summary = models.TextField(blank=True, help_text="A student-friendly simple summary of the session")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} ({self.template_type})"

class Activity(models.Model):
    session = models.ForeignKey(SessionPlan, on_delete=models.CASCADE, related_name='activities')
    step_name = models.CharField(max_length=100) # "Introduction", "Development", "Conclusion"
    
    # For Theory: "Home Group", "Expert Group", "Sharing" are steps in Development
    # For Practical: "Demonstration", "Practice", "Application" are steps
    
    trainer_activity = models.TextField()
    learner_activity = models.TextField()
    time_allocation = models.CharField(max_length=50, blank=True)
    resources_needed = models.TextField(blank=True)

    def __str__(self):
        return f"{self.session.topic} - {self.step_name}"

class Assessment(models.Model):
    class AssessmentType(models.TextChoices):
        FORMATIVE = 'FA', _('Formative Assessment')
        INTEGRATED = 'IA', _('Integrated Assessment')
        SUMMATIVE = 'SA', _('Summative Assessment')

    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, related_name='assessments')
    session = models.ForeignKey(SessionPlan, on_delete=models.CASCADE, null=True, blank=True) # Keep for backward compatibility or linking to plans
    title = models.CharField(max_length=200)
    assessment_type = models.CharField(max_length=2, choices=AssessmentType.choices, default=AssessmentType.FORMATIVE)
    total_marks = models.FloatField(default=100.0)
    questions_json = models.JSONField(default=dict) # Stores { "mcq": [], "tf": [], "matching": [] }
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    term = models.CharField(max_length=10, choices=[('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')], default='Term 1')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_assessment_type_display()})"

class StudentMark(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.STUDENT})
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    score = models.FloatField()
    total_marks = models.FloatField(default=100)
    date_recorded = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.assessment.title}: {self.score}"

class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', _('Present')
        ABSENT = 'ABSENT', _('Absent')
        LATE = 'LATE', _('Late')

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.STUDENT}, related_name='student_attendance')
    
    # Link to Classroom or Module (Optional: can be linked to either)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendances')
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendances')
    
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.SET_NULL, null=True, blank=True, related_name='attendances')
    term = models.CharField(max_length=10, choices=[('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')], default='Term 1')
    date = models.DateField(default=datetime.date.today)
    time_recorded = models.TimeField(auto_now=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': CustomUser.Role.TEACHER}, related_name='teacher_attendance')

    class Meta:
        unique_together = ('student', 'date')

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = 'info', _('Info')
        SUCCESS = 'success', _('Success')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NotificationType.choices, default=NotificationType.INFO)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:20]}"

class AcademicYear(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="e.g. 2025-2026")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all other academic years
            AcademicYear.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-name']


class SystemSetting(models.Model):
    site_name = models.CharField(max_length=100, default="AMS PORTAL")
    site_logo = models.ImageField(upload_to='branding/', null=True, blank=True)
    enable_ai_quizzer = models.BooleanField(default=True)
    allow_public_registration = models.BooleanField(default=True)
    primary_color = models.CharField(max_length=20, default="#4f46e5")
    gemini_api_key = models.CharField(max_length=200, blank=True, default='', help_text="Google Gemini API key for AI quiz and session plan generation.")
    email_notify_marks = models.BooleanField(default=False, help_text="Email students when their marks are entered.")
    email_notify_announcements = models.BooleanField(default=False, help_text="Email students when a new announcement is posted.")
    email_notify_welcome = models.BooleanField(default=False, help_text="Email new users their login credentials when their account is created.")
    current_academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True, related_name='system_settings')
    current_term = models.CharField(
        max_length=10,
        choices=[('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')],
        default='Term 1',
        help_text="Active academic term. Student promotions are processed during Term 3."
    )

    
    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "Global System Settings"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class AuditLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"
class Announcement(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='announcements')
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.TEACHER})
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.classroom.name}"

    class Meta:
        ordering = ['-created_at']

# --- NEW TVET HIERARCHY MODELS ---

class Trade(models.Model):
    name = models.CharField(max_length=150) # e.g., "Software Development Level 4"
    sector = models.CharField(max_length=150, blank=True) # e.g., "ICT"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Curriculum(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='curriculums')
    title = models.CharField(max_length=200) # e.g., "RTQF Level 4 Software 2026"
    qualification_level = models.CharField(max_length=50, blank=True, null=True) # e.g., "Level 4"
    pdf_document = models.FileField(upload_to='curriculums/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.trade.name})"

class SyllabusModule(models.Model):
    curriculum = models.ForeignKey(Curriculum, on_delete=models.CASCADE, related_name='modules')
    code = models.CharField(max_length=50) # e.g., "ICT SDV 4 01"
    title = models.TextField() # e.g., "Develop Web Applications"
    
    def __str__(self):
        return f"{self.code} - {self.title}"

class LearningOutcome(models.Model):
    module = models.ForeignKey(SyllabusModule, on_delete=models.CASCADE, related_name='learning_outcomes')
    title = models.TextField() # e.g., "LO2: Create database"

    def __str__(self):
        return self.title

class IndicativeContent(models.Model):
    learning_outcome = models.ForeignKey(LearningOutcome, on_delete=models.CASCADE, related_name='indicative_contents')
    title = models.TextField() # e.g., "IC1: Database schemas"

    def __str__(self):
        return self.title

class Topic(models.Model):
    indicative_content = models.ForeignKey(IndicativeContent, on_delete=models.CASCADE, related_name='topics')
    title = models.TextField() # e.g., "Primary Keys and Foreign Keys"

    def __str__(self):
        return self.title
