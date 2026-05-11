import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ams_project.settings')
django.setup()

from core.models import StudentMark, StudentProfile, CustomUser
print(f'Marks: {StudentMark.objects.count()}')
print(f'Students: {StudentProfile.objects.count()}')
print(f'User Students: {CustomUser.objects.filter(role="STUDENT").count()}')
