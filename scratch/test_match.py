import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ams_project.settings')
django.setup()

from core.models import SessionPlan, StudentMark, CustomUser, Module

print("=== Diagnostic Start ===")

# Find session plans containing "graphic" or "design"
sessions = SessionPlan.objects.filter(module__icontains="design")
print(f"Found {sessions.count()} design session plans:")
for s in sessions:
    print(f"  Session ID: {s.id}")
    print(f"    Module Field: {repr(s.module)}")
    print(f"    Topic: {repr(s.topic)}")
    print(f"    Level: {repr(s.level)}")

# Find students of Level 3
students = CustomUser.objects.filter(role="STUDENT")
print(f"\nTotal Student Accounts: {students.count()}")
for student in students:
    profile = getattr(student, 'student_profile', None)
    level = getattr(profile, 'level', 'None') if profile else 'No Profile'
    classroom = getattr(profile, 'classroom', None)
    class_name = classroom.name if classroom else 'No Class'
    print(f"  Student: {student.username} (Level: {level}, Class: {class_name})")
    
    # Get all marks for this student
    marks = StudentMark.objects.filter(student=student)
    print(f"    Marks Count: {marks.count()}")
    for m in marks:
        assessment = m.assessment
        mod = assessment.module if assessment else None
        mod_code = mod.module_code if mod else 'No Mod'
        mod_name = mod.module_name if mod else 'No Mod'
        session_plan = assessment.session if assessment else None
        session_id = session_plan.id if session_plan else 'No Session'
        print(f"      Mark ID: {m.id}")
        print(f"        Score: {m.score}/{m.total_marks}")
        print(f"        Assessment: {repr(assessment.title if assessment else 'N/A')}")
        print(f"        Module Code: {repr(mod_code)}, Name: {repr(mod_name)}")
        print(f"        Assessment Session ID: {session_id}")
        
        # Test match logic
        if s_plan := sessions.first():
            s_mod = s_plan.module.lower().strip() if s_plan.module else ''
            m_code = mod_code.lower() if mod_code else ''
            m_name = mod_name.lower() if mod_name else ''
            
            direct_match = (session_plan == s_plan)
            fuzzy_match = False
            if s_mod and (m_code or m_name):
                fuzzy_match = (m_code in s_mod or m_name in s_mod or s_mod in m_code or s_mod in m_name)
                
            print(f"        Match with Session {s_plan.id}: Direct={direct_match}, Fuzzy={fuzzy_match}")

print("=== Diagnostic End ===")
