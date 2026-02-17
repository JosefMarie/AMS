from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, SessionPlan, Activity, Assessment, StudentMark, Attendance, Classroom, Module

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 1

class SessionPlanAdmin(admin.ModelAdmin):
    list_display = ('topic', 'template_type', 'teacher', 'created_at')
    list_filter = ('template_type', 'teacher')
    inlines = [ActivityInline]

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'level', 'sex')
    search_fields = ('user__username', 'student_id')

class StudentMarkAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment', 'score', 'total_marks')
    list_filter = ('assessment', 'student__student_profile__level')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == CustomUser.Role.STUDENT:
            return qs.filter(student=request.user)
        return qs

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(SessionPlan, SessionPlanAdmin)
admin.site.register(Activity)
admin.site.register(Assessment)
admin.site.register(StudentMark, StudentMarkAdmin)
admin.site.register(Attendance)
admin.site.register(Classroom)
admin.site.register(Module)
