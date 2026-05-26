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
    raw_topic = range_text or kwargs.get('topic', 'General Topic')
    import re
    # Convert comma-separated or single-line topics to a numbered list
    if "," in raw_topic and "\n" not in raw_topic:
        topics_list = [t.strip() for t in raw_topic.split(",") if t.strip()]
        topic = "\n".join([f"{i+1}. {t}" for i, t in enumerate(topics_list)])
    elif "\n" in raw_topic:
        # Re-number or structure existing lines
        lines = [l.strip() for l in raw_topic.split("\n") if l.strip()]
        formatted = []
        for i, line in enumerate(lines):
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
            cleaned = re.sub(r'^-\s*', '', cleaned).strip()
            formatted.append(f"{i+1}. {cleaned}")
        topic = "\n".join(formatted)
    else:
        # Single topic: ensure numbered
        cleaned = re.sub(r'^\d+[\.\)]\s*', '', raw_topic).strip()
        cleaned = re.sub(r'^-\s*', '', cleaned).strip()
        topic = f"1. {cleaned}"
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

    # SMART Objectives Generation Logic based on Selected Topics & Template Type
    objective_items = []
    selected_topics_list = [t.strip() for t in re.split(r'[,;\n\r]', topic) if t.strip()]
    topics_clean = []
    for t in selected_topics_list:
        cleaned = re.sub(r'^(Module|Learning Outcome|Indicative Content|IC|LO):\s*', '', t, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'^\d+[\.\)]\s*', '', cleaned).strip()
        cleaned = re.sub(r'^-\s*', '', cleaned).strip()
        if cleaned:
            topics_clean.append(cleaned)
    if not topics_clean:
        topics_clean = [topic]
    is_practical = template_type.upper() == 'PRACTICAL'
    if is_practical:
        if len(topics_clean) == 1:
            objective_items = [
                f"1. By the end of this lesson, students will be able to demonstrate the setup and safety configuration for {topics_clean[0]}.",
                f"2. By the end of this lesson, students will be able to implement and execute practical procedures for {topics_clean[0]} safely and accurately.",
                f"3. By the end of this lesson, students will be able to test, debug, and troubleshoot operational issues related to {topics_clean[0]}."
            ]
        elif len(topics_clean) == 2:
            objective_items = [
                f"1. By the end of this lesson, students will be able to demonstrate hands-on setup, tools inspection, and safety checks for {topics_clean[0]}.",
                f"2. By the end of this lesson, students will be able to configure, construct, and operate tasks related to {topics_clean[1]}.",
                f"3. By the end of this lesson, students will be able to integrate, test, and troubleshoot a unified system combining {topics_clean[0]} and {topics_clean[1]}."
            ]
        else:
            objective_items = [
                f"1. By the end of this lesson, students will be able to demonstrate practical setup and tools inspection for {topics_clean[0]}.",
                f"2. By the end of this lesson, students will be able to implement, configure, and execute the procedures of {topics_clean[1]} successfully.",
                f"3. By the end of this lesson, students will be able to troubleshoot, maintain, and optimize tasks for {', '.join(topics_clean[2:])}."
            ]
    else:
        if len(topics_clean) == 1:
            objective_items = [
                f"1. By the end of this lesson, students will be able to define and explain the fundamental theoretical concepts of {topics_clean[0]}.",
                f"2. By the end of this lesson, students will be able to discuss and analyze the structure, operations, and use cases of {topics_clean[0]}.",
                f"3. By the end of this lesson, students will be able to evaluate and outline theoretical best practices when working with {topics_clean[0]}."
            ]
        elif len(topics_clean) == 2:
            objective_items = [
                f"1. By the end of this lesson, students will be able to explain the core principles and theoretical framework of {topics_clean[0]}.",
                f"2. By the end of this lesson, students will be able to describe and analyze the operations and theoretical behavior of {topics_clean[1]}.",
                f"3. By the end of this lesson, students will be able to compare, contrast, and discuss the relationships between {topics_clean[0]} and {topics_clean[1]}."
            ]
        else:
            objective_items = [
                f"1. By the end of this lesson, students will be able to describe the theoretical concepts and rules of {topics_clean[0]}.",
                f"2. By the end of this lesson, students will be able to explain, illustrate, and map the mechanisms of {topics_clean[1]}.",
                f"3. By the end of this lesson, students will be able to analyze, discuss, and summarize the theoretical aspects and applications of {', '.join(topics_clean[2:])}."
            ]
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
        "slow_learners_strategy": f"<p>1. Provide a step-by-step visual diagram/flowchart explaining <strong>{topic}</strong>.</p><p>2. Pair struggling students with advanced peers for collaborative review.</p>",
        "advanced_learners_strategy": f"<p>1. Assign a complex real-world extension challenge based on <strong>{topic}</strong>.</p><p>2. Direct them to design a comprehensive system architecture mapping this concept.</p>",
        "inclusivity_strategy": "<p>1. Offer large-font visual materials and dynamic captions.</p><p>2. Ensure physical/visual assistance options are highlighted and paired.</p>",
        "student_summary": f"<p>In this session, we will discover the core parameters of <strong>{topic}</strong>, exploring its real-world implementation, step-by-step applications, and practical tools to master this competency.</p>",
        "activities": activities
    }

def analyze_student_weakness(marks_data, user=None):
    """
    Uses Google Gemini AI (or mock fallback) to analyze a student's marks
    and suggest which module to study next based on their weak points.
    Supports Strategies B (exponential retry) and D (per-user keys).
    """
    from .ai_quiz_generator import get_api_key, gemini_call_with_retry
    GEMINI_API_KEY = get_api_key(user=user)
    
    if not GEMINI_API_KEY:
        # Fallback Mock logic
        lowest_module = min(marks_data, key=lambda x: marks_data[x]['score_percent'])
        return {
            "weakest_module": lowest_module,
            "analysis": f"Based on your scores, you should focus on {lowest_module}.",
            "advice": "Review the core concepts and practice previous assignments related to this module."
        }
        
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        
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
        response = gemini_call_with_retry(
            client,
            model='gemini-2.5-flash',
            contents=prompt
        )
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

def generate_advanced_session_plan_ai(syllabus_text, range_text, template_type='THEORY', user=None, **kwargs):
    """
    Uses Google Gemini AI to fully generate a comprehensive session plan,
    including timing, activities, objectives, and context.
    Provides a fallback to the standard static generator if API fails.
    Supports Strategies B (exponential retry) and D (per-user keys).
    """
    from google import genai
    from .ai_quiz_generator import get_api_key, gemini_call_with_retry
    GEMINI_API_KEY = get_api_key(user=user)
    
    if not GEMINI_API_KEY:
        print("No Gemini API key, falling back to static generation")
        return generate_session_plan_ai(syllabus_text, range_text, template_type, **kwargs)
        
    topic = range_text or kwargs.get('topic', 'General Topic')
    duration_str = str(kwargs.get('duration', '60'))
    technique = kwargs.get('facilitation_technique', 'Brainstorming')
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        Act as an expert TVET (Technical and Vocational Education and Training) Trainer.
        You need to generate a {template_type} session plan for a class on {topic}.
        The total duration of the class is {duration_str} minutes.
        The facilitation technique requested is {technique}.
        
        CRITICAL OBJECTIVE INSTRUCTIONS:
        1. Generate EXACTLY 3 objectives strictly based on the specific selected topics ({topic}), NOT the whole syllabus.
        2. Always use Bloom's Taxonomy action verbs (e.g., Analyze, Design, Evaluate, Construct, Explain).
        3. NEVER include raw syllabus headers or prefixes like "Module: ...", "Learning Outcome: ...", or "Indicative Content: ..." in the objectives. Focus directly on the concrete topic.
        4. For THEORY sessions ({template_type} == 'THEORY'), focus all 3 objectives on cognitive theoretical understanding (e.g., Explain, Discuss, Analyze, Compare).
        5. For PRACTICAL sessions ({template_type} == 'PRACTICAL'), focus all 3 objectives on hands-on, psychomotor, and troubleshooting performance skills (e.g., Demonstrate, Implement, Configure, Troubleshoot).
        6. For "topic": List the selected topics strictly as a formatted numbered or bulleted list (e.g., "1. Topic A\n2. Topic B"), NOT as a paragraph. Keep "range_details" as a paragraph describing the scope/range.
        7. Provide 2-3 specific technical or pedagogical references/citations for these topics in the "references" field.
        8. Provide highly custom and specific differentiated strategies in HTML paragraphs (<p>...<p>) for slow learners, advanced learners, and inclusivity accommodations. Generate a student-friendly visual/interactive lesson summary for students to view.
        
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
            "topic": "1. Selected Topic A\\n2. Selected Topic B...",
            "objectives": "Knowledge Objectives:\\n1. By the end of this lesson...\\nSkill Objectives:\\n2. By the end of this lesson...",
            "facilitation_technique": "{technique}",
            "resources": "Projector, Task sheets, etc.",
            "indicative_content": "Summary of the content (bulleted list)...",
            "range_details": "Paragraph describing the range/scope...",
            "duration": "{duration_str} min",
            "reflection": "Post-session reflection placeholder",
            "references": "1. Reference Book/Doc A\\n2. Reference Book/Doc B...",
            "slow_learners_strategy": "<p>Specific supportive strategy in HTML paragraphs...</p>",
            "advanced_learners_strategy": "<p>Specific extension strategy in HTML paragraphs...</p>",
            "inclusivity_strategy": "<p>Specific accessibility strategy in HTML paragraphs...</p>",
            "student_summary": "<p>A student-friendly simple summary of the session in HTML paragraphs...</p>",
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
        
        response = gemini_call_with_retry(
            client,
            model='gemini-2.5-flash',
            contents=prompt
        )
        result_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(result_text)
        
    except Exception as e:
        print(f"Gemini Advanced Session Plan error: {e}")
        return generate_session_plan_ai(syllabus_text, range_text, template_type, **kwargs)
