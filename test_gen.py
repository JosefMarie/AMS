
import sys
import os
import re

def generate_session_plan_ai(syllabus_text, range_text, template_type='THEORY', **kwargs):
    topic = range_text or kwargs.get('topic', 'General Topic')
    technique = kwargs.get('facilitation_technique', 'Brainstorming')
    duration_str = str(kwargs.get('duration', '60'))
    
    duration_match = re.search(r'\d+', duration_str)
    total_minutes = int(duration_match.group()) if duration_match else 60

    syllabus_lines = [l.strip() for l in syllabus_text.split('\n') if len(l.strip()) > 15]
    extracted_objectives = syllabus_lines[:3] if syllabus_lines else ["Understand the core concepts of " + topic]
    dev_content_pool = syllabus_lines[3:8] if len(syllabus_lines) > 3 else syllabus_lines
    dev_summary = " ".join(dev_content_pool[:2]) if dev_content_pool else topic

    intro_time = max(10, int(total_minutes * 0.10))
    concl_total = max(20, int(total_minutes * 0.30))
    dev_time = total_minutes - intro_time - concl_total
    
    summary_time = int(concl_total * 0.3)
    assess_time = int(concl_total * 0.4)
    eval_time = concl_total - summary_time - assess_time

    activities = []
    
    # Simpler trainer activity for core test
    intro_trainer = f"Introduction with {topic}. Objectives: {', '.join(extracted_objectives[:2])}."
    activities.append({"step_name": "Intro", "trainer": intro_trainer, "learner": "Listen", "time": f"{intro_time} min"})

    # ... rest of logic simplified for speed test ...
    return {"status": "ok", "activities": activities}

# Test execution with large syllabus
syllabus = "LOREM IPSUM DOLOR SIT AMET CONSECTETUR ADIPISCING ELIT " * 1000 + "\n"
syllabus = syllabus * 10 
print("Starting test with large syllabus...")
import time
start = time.time()
result = generate_session_plan_ai(syllabus, "Python Programming")
end = time.time()
print(f"Success in {end - start:.4f}s!")
