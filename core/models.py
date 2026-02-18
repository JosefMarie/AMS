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

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

class Classroom(models.Model):
    name = models.CharField(max_length=100) # e.g., "Level 4 Software"
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.TEACHER}, related_name='classrooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

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
    level = models.CharField(max_length=50, blank=True) # made blank=True as classroom might define this
    sex = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])

    def generate_student_id(self):
        # Logic: L{Level}-YEAR-RANDOM (e.g., L4-2026-4821)
        # Try to deduce level from classroom name or default to 'Gen'
        lvl_code = "Gen"
        if self.classroom and "Level" in self.classroom.name:
             # Extract "Level X" -> "LX"
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
            # Ensure uniqueness
            while StudentProfile.objects.filter(student_id=self.student_id).exists():
                 self.student_id = self.generate_student_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.student_id})"

class SessionPlan(models.Model):
    class TemplateType(models.TextChoices):
        THEORY = "THEORY", _("Delivering (Theory)")
        PRACTICAL = "PRACTICAL", _("Practical")

    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': CustomUser.Role.TEACHER})
    trainer_name = models.CharField(max_length=100, blank=True)
    template_type = models.CharField(max_length=20, choices=TemplateType.choices, default=TemplateType.THEORY)
    
    # Common Fields
    sector = models.CharField(max_length=100)
    trade = models.CharField(max_length=100)
    level = models.CharField(max_length=50, blank=True)
    class_name = models.CharField(max_length=100, blank=True)
    num_students = models.IntegerField(null=True, blank=True)
    academic_year = models.CharField(max_length=50, blank=True)
    term = models.CharField(max_length=50, blank=True)
    weeks = models.CharField(max_length=50, blank=True)
    module = models.CharField(max_length=100) # e.g., Software Development
    learning_outcome = models.TextField()
    indicative_content = models.TextField(blank=True)
    performance_criteria = models.TextField(blank=True, help_text="Specific performance criteria from RTB curriculum")
    pre_requisite_knowledge = models.TextField(blank=True, help_text="Link to previous lessons or required prior knowledge")
    cross_cutting_issues = models.TextField(blank=True, help_text="Gender, Environment, Inclusive education, etc.")
    hse_considerations = models.TextField(blank=True, help_text="Health, Safety, and Environment considerations")
    ict_tools = models.TextField(blank=True, help_text="ICT tools used for facilitation")
    special_needs_support = models.TextField(blank=True, help_text="Support for students with special educational needs")
    
    # Specific Fields
    topic = models.CharField(max_length=200)
    objectives = models.TextField()
    facilitation_technique = models.CharField(max_length=100, blank=True) # e.g. Jig-saw
    resources = models.TextField(blank=True)
    
    # Practical specific
    range_details = models.TextField(blank=True, help_text="Range of variables")
    duration = models.CharField(max_length=50, blank=True) # e.g. "2 Hours"
    reflection = models.TextField(blank=True)

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
    
    date = models.DateField(default=datetime.date.today)
    time_recorded = models.TimeField(auto_now=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': CustomUser.Role.TEACHER}, related_name='teacher_attendance')

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student.username} - {self.date} - {self.status}"
