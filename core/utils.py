import json
import random

def generate_quiz_from_text(text):
    """
    Mock function to simulate AI Quiz Generation.
    In a real scenario, this would call OpenAI API.
    """
    # Simulate processing delay
    # ...
    
    # Mock Response
    quiz_data = {
        "mcq": [
            {
                "question": "What is the primary purpose of this module?",
                "options": ["To learn Python", "To learn Django", "To manage sessions", "All of the above"],
                "answer": "To manage sessions"
            },
            {
                "question": "Which file is used for URL configuration?",
                "options": ["models.py", "views.py", "urls.py", "admin.py"],
                "answer": "urls.py"
            },
            {
                "question": "What does MVC stand for in Django context?",
                "options": ["Model View Controller", "Model View Template", "Main View Control", "None"],
                "answer": "Model View Template"
            },
            {
                "question": "Which command runs the development server?",
                "options": ["runserver", "startapp", "migrate", "test"],
                "answer": "runserver"
            },
            {
                "question": "What is the default database for Django?",
                "options": ["PostgreSQL", "MySQL", "SQLite", "Oracle"],
                "answer": "SQLite"
            }
        ],
        "true_false": [
            {"question": "Django is written in Java.", "answer": "False"},
            {"question": "SQLite is a serverless database.", "answer": "True"},
            {"question": "Templates are used for database schema.", "answer": "False"},
            {"question": "Views handle the request processing.", "answer": "True"},
            {"question": "Admin interface is built-in.", "answer": "True"}
        ],
        "matching": [
            {"term": "Model", "definition": "Data Structure"},
            {"term": "View", "definition": "Business Logic"},
            {"term": "Template", "definition": "Presentation Layer"},
            {"term": "URL", "definition": "Routing"},
            {"term": "Admin", "definition": "Management"}
        ]
    }
    
    return quiz_data

def generate_session_plan_ai(syllabus_text, range_text, template_type='THEORY', **kwargs):
    """
    Simulates AI Session Plan Generation based on syllabus and range.
    Objectives and Development content are now derived directly from analyzing the syllabus text.
    """
    topic = range_text or kwargs.get('topic', 'General Topic')
    technique = kwargs.get('facilitation_technique', 'Brainstorming')
    duration_str = str(kwargs.get('duration', '60'))
    
    import re
    duration_match = re.search(r'\d+', duration_str)
    total_minutes = int(duration_match.group()) if duration_match else 60

    # Syllabus Analysis Logic (Simulating AI extraction)
    # Split syllabus into lines and filter for content-rich lines (length > 15)
    syllabus_lines = [l.strip() for l in syllabus_text.split('\n') if len(l.strip()) > 15]
    
    # Extract Objectives from syllabus (first 3 useful lines)
    extracted_objectives = syllabus_lines[:3] if syllabus_lines else ["Understand the core concepts of " + topic]
    
    # Extract Development Content (lines after the first 3 or specific keywords)
    dev_content_pool = syllabus_lines[3:8] if len(syllabus_lines) > 3 else syllabus_lines
    dev_summary = " ".join(dev_content_pool[:2]) if dev_content_pool else topic

    # pedagogical timing distribution
    intro_time = max(10, int(total_minutes * 0.10))
    concl_total = max(20, int(total_minutes * 0.30))
    dev_time = total_minutes - intro_time - concl_total
    
    summary_time = int(concl_total * 0.3)
    assess_time = int(concl_total * 0.4)
    eval_time = concl_total - summary_time - assess_time

    activities = []
    
    # 1. Introduction
    intro_trainer = (
        f"1. Greets the trainees warmly and establishes a positive learning atmosphere.\n"
        f"2. Takes the roll call to ensure attendance and readiness.\n"
        f"3. Involves learners in setting or reviewing ground rules for engagement.\n"
        f"4. Asks curiosity-piquing questions about what they remember from the last session related to {topic}.\n"
        f"5. Introduces the new topic: '{topic}' with a compelling hook.\n"
        f"6. Involves learners in reading and explaining the session objectives: {', '.join(extracted_objectives[:2])}."
    )
    intro_learner = (
        "1. Respond to the greetings.\n"
        "2. Respond to the roll call.\n"
        "3. Participate in setting/reviewing ground rules.\n"
        "4. Provide answers to the questions asked by the trainer based on prior knowledge.\n"
        "5. Ask for clarification if any.\n"
        "6. Read and explain the objectives of the session and ask for clarification if any."
    )
    activities.append({
        "step_name": "Introduction", 
        "trainer": intro_trainer, 
        "learner": intro_learner, 
        "time": f"{intro_time} min"
    })

    if template_type.upper() == 'PRACTICAL':
        # 2. Practical Development
        prep_trainer = (
            f"1. Briefs learners on Health, Safety, and Environment (HSE) protocols for {topic}.\n"
            f"2. Inspects tools, equipment, and Personal Protective Equipment (PPE) for readiness.\n"
            f"3. Explains the practical task: {dev_summary}."
        )
        prep_learner = (
            "1. Put on required PPE and verify tool safety.\n"
            "2. Listen to safety instructions and clarify any doubts.\n"
            "3. Confirm understanding of the task requirements."
        )
        activities.append({
            "step_name": "Step 1: Preparation & Safety Briefing",
            "trainer": prep_trainer,
            "learner": prep_learner,
            "time": f"{int(dev_time * 0.15)} min"
        })

        demo_trainer = (
            f"1. Demonstrates the step-by-step procedure of {topic} focusing on: {dev_summary}.\n"
            f"2. Explains the 'Why' behind each step to ensure technical understanding.\n"
            f"3. Encourages learners to ask questions during the demonstration."
        )
        demo_learner = (
            "1. Observe the demonstration closely.\n"
            "2. Take notes on key safety points and technical steps.\n"
            "3. Ask clarifying questions on the demonstrated procedure."
        )
        activities.append({
            "step_name": "Step 2: Trainer Demonstration (I Do)",
            "trainer": demo_trainer,
            "learner": demo_learner,
            "time": f"{int(dev_time * 0.25)} min"
        })

        guided_trainer = (
            f"1. Supervises learners as they begin the practical task: {dev_summary}.\n"
            f"2. Provides immediate corrective feedback and guidance.\n"
            f"3. Ensures all safety protocols are strictly followed during practice."
        )
        guided_learner = (
            "1. Perform the task under the close supervision of the trainer.\n"
            "2. Apply the feedback provided to improve performance.\n"
            "3. Help peers where possible in a collaborative environment."
        )
        activities.append({
            "step_name": "Step 3: Guided Practice (We Do)",
            "trainer": guided_trainer,
            "learner": guided_learner,
            "time": f"{int(dev_time * 0.35)} min"
        })

        indep_trainer = (
            f"1. Monitors learners as they work independently on {topic}.\n"
            f"2. Evaluates individual performance against the criteria: {dev_summary}.\n"
            f"3. Manages time and prepares for session conclusion."
        )
        indep_learner = (
            "1. Perform the complete practical task independently.\n"
            "2. Show competence and adherence to safety standards.\n"
            "3. Finalize the task and prepare for evaluation."
        )
        activities.append({
            "step_name": "Step 4: Independent Practice (You Do)",
            "trainer": indep_trainer,
            "learner": indep_learner,
            "time": f"{int(dev_time * 0.25)} min"
        })
    else:
        # 2. Theory Development
        s1_trainer = (
            f"Is forming groups and distributing content from the syllabus regarding: {dev_summary}. "
            f"Gives instruction on how the groups will be formed (e.g., counting 1-4)."
        )
        s1_learner = "Forming the group. Participating in forming groups by counting and joining peers with the same number."
        activities.append({
            "step_name": "Development Step 1: Forming Groups",
            "trainer": s1_trainer,
            "learner": s1_learner,
            "time": f"{int(dev_time * 0.15)} min"
        })

        s2_trainer = (
            f"- Distributing task sheets focused on: {dev_summary}.\n"
            "- Explaining the instructions based on syllabus module content.\n"
            "- Monitors the group discussion and reminds them to use their time accordingly."
        )
        s2_learner = (
            "- Receiving the task.\n"
            "- Learner can ask for clarification and start discussion.\n"
            f"- Explore deeply the task sheet and extracted content: {dev_summary}."
        )
        activities.append({
            "step_name": f"Development Step 2: {technique} / Expert Group Discussion",
            "trainer": s2_trainer,
            "learner": s2_learner,
            "time": f"{int(dev_time * 0.50)} min"
        })

        s3_trainer = (
            f"- Ask learners to share what they got from the syllabus content: {dev_summary}.\n"
            "- Monitor group discussion and announce the time for each member/group."
        )
        s3_learner = (
            "- Each learner starts to explain to others what he or she learned from the extracted syllabus content.\n"
            "- Continue their discussion and ask for clarification if any."
        )
        activities.append({
            "step_name": "Development Step 3: Discussion and Sharing groups",
            "trainer": s3_trainer,
            "learner": s3_learner,
            "time": f"{int(dev_time * 0.35)} min"
        })

    # 3. Conclusion
    activities.append({
        "step_name": "Summary", 
        "trainer": "The trainer involves learners in session summary by asking questions related to the syllabus content extracted.", 
        "learner": "Learners participate in session summary by answering the trainer’s questions.", 
        "time": f"{summary_time} min"
    })

    activities.append({
        "step_name": "Assessment/Assignment", 
        "trainer": f"Trainer provides assessment based on: {dev_summary}.", 
        "learner": "Learner clarifies doubts and starts the assessment.", 
        "time": f"{assess_time} min"
    })

    activities.append({
        "step_name": "Evaluation", 
        "trainer": "Trainer involves learners in evaluating the session. Closes session.", 
        "learner": "Learner responds to questions and prepares for the next session.", 
        "time": f"{eval_time} min"
    })

    # Resources, HSE, Cross-cutting
    base_resources = ["Attendance list", "Projector", "Computer", "Blackboard", "Chalk", "Flip chart", "Marker pen"]
    final_resources = ", ".join(base_resources + ["Task sheets", "Quiz sheet", "Handouts"])

    # Rwandan TVET Logic (HSE, Cross-cutting, ICT)
    hse_map = {
        "Welding": "Ensure use of welding masks, leather gloves, and protective aprons. Check ventilation.",
        "Electricity": "Ensure all circuits are isolated before touching. Use insulated tools.",
        "Computer": "Ensure proper sitting posture (ergonomics).",
        "Mechanic": "Wear safety boots and overalls.",
        "Building": "Wear helmets and safety harnesses."
    }
    hse_text = hse_map.get(next((k for k in hse_map if k.lower() in topic.lower()), None), "Ensure a clean work environment, proper lighting, and check for hazards.")

    cross_cutting = (
        "1. Gender Equality: Ensure both male and female trainees participate equally.\n"
        "2. Environment & Sustainability: Minimize paper waste.\n"
        "3. Peace & Values: Promote collaborative work."
    )
    ict_tools = "Digital projector, simulation software, and internet access."
    special_needs = "Provide large-print handouts and ensure accessibility."

    # SMART Objectives Generation Logic
    objective_items = []
    stem = "By the end of this lesson, students will be able to"
    
    nvqf_level = str(kwargs.get('level', '4'))
    if "5" in nvqf_level:
        verbs = ["analyze", "evaluate", "implement"]
    elif "3" in nvqf_level:
        verbs = ["list", "identify", "describe"]
    else:
        verbs = ["explain", "demonstrate", "discuss"]

    for i, line in enumerate(extracted_objectives[:3]):
        # Remove common bullet points or numbering
        clean_line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
        if not clean_line.lower().startswith("by the end"):
            objective_items.append(f"{i+1}. {stem} {verbs[i % len(verbs)]} {clean_line}.")
        else:
            objective_items.append(f"{i+1}. {clean_line}")

    if not objective_items:
        objective_items = [f"1. {stem} {verbs[0]} the key principles of {topic}."]

    objectives_text = "\n".join(objective_items)

    return {
        "sector": kwargs.get('sector', 'General'),
        "trade": kwargs.get('trade', 'General'),
        "level": kwargs.get('level', 'N/A'),
        "class_name": kwargs.get('class_name', 'N/A'),
        "num_students": kwargs.get('num_students', 0),
        "trainer_name": kwargs.get('trainer_name', ''),
        "academic_year": kwargs.get('academic_year', '2025/2026'),
        "term": kwargs.get('term', 'Term 1'),
        "weeks": kwargs.get('weeks', '1'),
        "module": kwargs.get('module_name', 'General Module'),
        "learning_outcome": kwargs.get('learning_outcome', 'Competency demonstration.'),
        "performance_criteria": kwargs.get('performance_criteria', 'According to standard operating procedures.'),
        "pre_requisite_knowledge": kwargs.get('pre_requisite_knowledge', 'Basic understanding level.'),
        "cross_cutting_issues": cross_cutting,
        "hse_considerations": hse_text,
        "ict_tools": ict_tools,
        "special_needs_support": special_needs,
        "topic": topic,
        "objectives": objectives_text,
        "facilitation_technique": technique,
        "resources": final_resources,
        "indicative_content": dev_summary,
        "range_details": topic,
        "duration": f"{total_minutes} min",
        "reflection": "Session conducted successfully based on syllabus content.",
        "activities": activities
    }

def analyze_student_weakness(marks_data):
    """
    Uses Google Gemini AI (or mock fallback) to analyze a student's marks
    and suggest which module to study next based on their weak points.
    """
    import google.generativeai as genai
    from .ai_quiz_generator import GEMINI_API_KEY
    
    if not GEMINI_API_KEY:
        # Fallback Mock logic
        lowest_module = min(marks_data, key=lambda x: marks_data[x]['score_percent'])
        return {
            "weakest_module": lowest_module,
            "analysis": f"Based on your scores, you should focus on {lowest_module}.",
            "advice": "Review the core concepts and practice previous assignments related to this module."
        }
        
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Analyze the following student assessment marks and identify their weakest area.
        Provide a short, encouraging analysis, and suggest specific study strategies.
        
        Marks data:
        {json.dumps(marks_data, indent=2)}
        
        Return ONLY a JSON object with this structure, no markdown formatting:
        {{
            "weakest_module": "Module Name",
            "analysis": "Short encouraging analysis of their performance...",
            "advice": "Actionable advice on how to improve..."
        }}
        """
        response = model.generate_content(prompt)
        # Parse the JSON response
        result_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(result_text)
    except Exception as e:
        print(f"AI weakness analysis error: {e}")
        # Fallback Mock logic
        lowest_module = min(marks_data, key=lambda x: marks_data[x]['score_percent'])
        return {
            "weakest_module": lowest_module,
            "analysis": f"Based on your scores, it looks like {lowest_module} is your weakest point.",
            "advice": "Try reviewing your previous class notes and ask your trainer for extra help."
        }

def generate_advanced_session_plan_ai(syllabus_text, range_text, template_type='THEORY', **kwargs):
    """
    Uses Google Gemini AI to fully generate a comprehensive session plan,
    including timing, activities, objectives, and context.
    Provides a fallback to the standard static generator if API fails.
    """
    import google.generativeai as genai
    from .ai_quiz_generator import GEMINI_API_KEY
    
    if not GEMINI_API_KEY:
        print("No Gemini API key, falling back to static generation")
        return generate_session_plan_ai(syllabus_text, range_text, template_type, **kwargs)
        
    topic = range_text or kwargs.get('topic', 'General Topic')
    duration_str = str(kwargs.get('duration', '60'))
    technique = kwargs.get('facilitation_technique', 'Brainstorming')
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Act as an expert TVET (Technical and Vocational Education and Training) Trainer.
        You need to generate a {template_type} session plan for a class on {topic}.
        The total duration of the class is {duration_str} minutes.
        The facilitation technique requested is {technique}.
        
        Syllabus Context:
        {syllabus_text}
        
        Return ONLY a JSON object with this exact structure. Do not use Markdown formatting for the JSON block itself.
        {{
            "sector": "{kwargs.get('sector', 'General')}",
            "trade": "{kwargs.get('trade', 'General')}",
            "level": "{kwargs.get('level', 'N/A')}",
            "class_name": "{kwargs.get('class_name', 'N/A')}",
            "num_students": {kwargs.get('num_students', 0)},
            "trainer_name": "{kwargs.get('trainer_name', '')}",
            "academic_year": "{kwargs.get('academic_year', '2025/2026')}",
            "term": "{kwargs.get('term', 'Term 1')}",
            "weeks": "{kwargs.get('weeks', '1')}",
            "module": "{kwargs.get('module_name', 'General Module')}",
            "learning_outcome": "Generate a concise learning outcome based on syllabus",
            "performance_criteria": "Generate 1-2 performance criteria",
            "pre_requisite_knowledge": "Generate what they should already know",
            "cross_cutting_issues": "1. Gender Equality...\\n2. Environment...",
            "hse_considerations": "Specific Health and Safety requirements for this topic",
            "ict_tools": "Tools needed...",
            "special_needs_support": "How to support students...",
            "topic": "{topic}",
            "objectives": "1. By the end of this lesson, students will be able to...\\n2. ...",
            "facilitation_technique": "{technique}",
            "resources": "Projector, Task sheets, etc.",
            "indicative_content": "Summary of the content...",
            "range_details": "{topic}",
            "duration": "{duration_str} min",
            "reflection": "Post-session reflection placeholder",
            "activities": [
                {{
                    "step_name": "Introduction",
                    "trainer": "What the trainer does (numbered list)",
                    "learner": "What the learner does (numbered list)",
                    "time": "10 min"
                }},
                {{
                    "step_name": "Development Step 1...",
                    "trainer": "...",
                    "learner": "...",
                    "time": "20 min"
                }}
            ]
        }}
        
        Make sure the activities' times add up to exactly {duration_str} minutes. Provide 4-6 activity steps.
        If it's a PRACTICAL session, focus the steps on Preparation, Demonstration (I do), Guided Practice (We do), Independent Practice (You do), and Evaluation.
        If it's a THEORY session, focus on Introduction, Group Discussion, Sharing, Summary, Assessment, and Evaluation.
        """
        
        response = model.generate_content(prompt)
        result_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(result_text)
        
    except Exception as e:
        print(f"Gemini Advanced Session Plan error: {e}")
        return generate_session_plan_ai(syllabus_text, range_text, template_type, **kwargs)
