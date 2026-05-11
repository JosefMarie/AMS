import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ams_project.settings')
django.setup()

from core.models import CustomUser

students = CustomUser.objects.filter(role=CustomUser.Role.STUDENT)
print(f"Total students: {students.count()}")
for s in students[:10]:
    print(f"Student: {s.username}, Joined: {s.date_joined}")

now = timezone.now()
for i in range(5, -1, -1):
    month_start = (now - timedelta(days=i*30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    count = CustomUser.objects.filter(
        role=CustomUser.Role.STUDENT,
        date_joined__range=(month_start, month_end)
    ).count()
    print(f"Period: {month_start.strftime('%b %Y')} to {month_end.strftime('%b %Y')}, Count: {count}")
