import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ams_project.settings')
django.setup()

from core.models import StudentProfile

boys = StudentProfile.objects.filter(sex='Male').count()
girls = StudentProfile.objects.filter(sex='Female').count()
print(f"Boys: {boys}, Girls: {girls}")
