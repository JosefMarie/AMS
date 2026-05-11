import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ams_project.settings')
django.setup()

from core.models import StudentMark
from django.db.models import Avg

marks = StudentMark.objects.all()
for m in marks:
    print(f"Mark ID: {m.id}, Score: {m.score}, Total: {m.total_marks}, Module: {m.assessment.module.module_name if m.assessment and m.assessment.module else 'N/A'}")

module_performance = StudentMark.objects.values('assessment__module__module_name')\
    .annotate(avg_score=Avg('score'), avg_total=Avg('total_marks'))\
    .order_by('-avg_score')[:7]

print(f"Module Performance Rows: {len(module_performance)}")
for item in module_performance:
    print(item)
