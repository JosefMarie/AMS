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
    Now follows the detailed 'Delivering' template logic.
    """
    topic = range_text or kwargs.get('topic', 'General Topic')
    technique = kwargs.get('facilitation_technique', 'Brainstorming')
    duration_str = str(kwargs.get('duration', '60'))
    
    import re
    duration_match = re.search(r'\d+', duration_str)
    total_minutes = int(duration_match.group()) if duration_match else 60

    # pedagogical timing distribution
    # Intro (~10%), Development (~60%), Conclusion (Summary/Assess/Eval ~30%)
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
        f"6. Involves learners in reading and explaining the session objectives to ensure ownership."
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
        # 2. Practical Development - Demo - Practice - Apply
        # Step 1: Preparation & Safety
        prep_trainer = (
            f"1. Briefs learners on Health, Safety, and Environment (HSE) protocols for {topic}.\n"
            f"2. Inspects tools, equipment, and Personal Protective Equipment (PPE) for readiness.\n"
            f"3. Explains the practical task and the required performance criteria."
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

        # Step 2: Demonstration
        demo_trainer = (
            f"1. Demonstrates the step-by-step procedure of {topic} clearly and slowly.\n"
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

        # Step 3: Guided Practice
        guided_trainer = (
            f"1. Supervises learners as they begin the practical task of {topic}.\n"
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

        # Step 4: Independent Practice
        indep_trainer = (
            f"1. Monitors learners from a distance as they work independently.\n"
            f"2. Evaluates individual performance against the criteria.\n"
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
        # 2. Theory Development - Structured Steps 1, 2, 3
        # Step 1: Forming Groups
        s1_trainer = (
            f"Is forming groups. Trainer's activity: Involves the learners by giving instruction on how the groups will be "
            f"done and formed like involving the learner by counting 1 up to 4 (depending on class size). "
            f"Asks learners to name their group and join their respective group so the students with the same number will be in one group."
        )
        s1_learner = "Forming the group. Name their group, participating in forming groups by counting and joining peers with the same number."
        activities.append({
            "step_name": "Development Step 1: Forming Groups",
            "trainer": s1_trainer,
            "learner": s1_learner,
            "time": f"{int(dev_time * 0.15)} min"
        })

        # Step 2: Expert/Task Discussion
        s2_trainer = (
            "- Distributing the task sheets to groups.\n"
            "- Explaining the instruction regarding the tasks.\n"
            "- Monitors the group discussion and reminds them to use their time accordingly.\n"
            "- Declares the end of discussion."
        )
        s2_learner = (
            "- Receiving the task.\n"
            "- Learner can ask for clarification if there is any and start discussion.\n"
            "- Explore deeply the task sheet and indicative content.\n"
            "- End the discussion."
        )
        activities.append({
            "step_name": f"Development Step 2: {technique} / Expert Group Discussion",
            "trainer": s2_trainer,
            "learner": s2_learner,
            "time": f"{int(dev_time * 0.50)} min"
        })

        # Step 3: Discussion and Sharing groups
        s3_trainer = (
            "- Ask learners to share what they got from their groups.\n"
            "- Monitor group discussion and announce the time for each member/group.\n"
            "- Declare the end of group discussion and tell learners to go back to their respective seats."
        )
        s3_learner = (
            "- Each learner starts to explain to others what he or she learned in his or her group.\n"
            "- Continue their discussion and ask for clarification if any.\n"
            "- End of discussion and go back to their respective seats."
        )
        activities.append({
            "step_name": "Development Step 3: Discussion and Sharing groups",
            "trainer": s3_trainer,
            "learner": s3_learner,
            "time": f"{int(dev_time * 0.35)} min"
        })

    # 3. Conclusion (Summary, Assessment, Evaluation)
    # Conclusion (Summary, Assessment, Evaluation)
    activities.append({
        "step_name": "Summary", 
        "trainer": "The trainer involves learners in session summary by asking some questions related to the objectives of the session.", 
        "learner": "Learners participate in session summary by answering the trainer’s questions related to the objectives of the session.", 
        "time": f"{summary_time} min"
    })

    activities.append({
        "step_name": "Assessment/Assignment", 
        "trainer": "Trainer provides the instructions about the assessment, clarifes doubts, and declares the end of assessment, asking learners to submit.", 
        "learner": "Learner asks for clarification if any and starts the assessment. Submit finally the quiz sheets.", 
        "time": f"{assess_time} min"
    })

    activities.append({
        "step_name": "Evaluation", 
        "trainer": "The trainer involves learners in evaluating the session by asking them how the session was conducted. Announces next topic and closes session.", 
        "learner": "Learner participates in evaluating the session by responding to questions and taking attention to the next session.", 
        "time": f"{eval_time} min"
    })

    # Juicy Resources Generation
    base_resources = ["Attendance list", "Projector", "Computer", "Blackboard", "Chalk", "Flip chart", "Marker pen"]
    topic_map = {
        "Python": ["IDEs", "Notebooks", "Python Documentation"],
        "Web": ["Browsers", "VS Code", "HTML/CSS Reference"],
        "Data": ["SQL Workbench", "Database Schema", "Sample Data"],
        "Mechanic": ["Wrench", "Bolts", "Safety Goggles"],
        "Welding": ["Welding Machine", "Electrodes", "Mask", "Gloves"]
    }
    juicy = []
    for k, v in topic_map.items():
        if k.lower() in topic.lower():
            juicy.extend(v)
    
    final_resources = ", ".join(base_resources + juicy + ["Task sheets", "Quiz sheet", "Handouts"])

    # Rwandan TVET Logic (HSE, Cross-cutting, ICT)
    hse_map = {
        "Welding": "Ensure use of welding masks, leather gloves, and protective aprons. Check ventilation.",
        "Electricity": "Ensure all circuits are isolated before touching. Use insulated tools.",
        "Computer": "Ensure proper sitting posture (ergonomics) to avoid back pain and eye strain.",
        "Mechanic": "Wear safety boots and overalls. Ensure the vehicle is properly supported by jack stands.",
        "Building": "Wear helmets and safety harnesses when working at heights."
    }
    hse_default = "Ensure a clean work environment, proper lighting, and check for any tripping hazards."
    hse_text = hse_default
    for k, v in hse_map.items():
        if k.lower() in topic.lower():
            hse_text = v
            break

    cross_cutting = (
        "1. Gender Equality: Ensure both male and female trainees participate equally in group presentations.\n"
        "2. Environment & Sustainability: Minimize paper waste by using digital handouts where possible.\n"
        "3. Peace & Values: Promote collaborative work and respect for diverse opinions during group discussions."
    )

    ict_tools = "Digital projector, simulation software related to the topic, and internet access for research."
    special_needs = "Provide large-print handouts for students with visual impairment and ensure the room is accessible for trainers with physical disabilities."

    # SMART Objectives Generation Logic
    # 1. Stem: "By the end of this lesson, students will be able to..."
    # 2. Bloom's Verbs
    blooms_verbs = {
        "Remember": ["identify", "list", "define", "label", "match"],
        "Understand": ["explain", "describe", "discuss", "summarize", "interpret"],
        "Apply": ["apply", "demonstrate", "calculate", "simulate", "implement"],
        "Analyze": ["analyze", "compare", "classify", "differentiate", "organize"],
        "Evaluate": ["evaluate", "judge", "critique", "verify", "justify"],
        "Create": ["design", "construct", "produce", "compose", "develop"]
    }
    
    # Rwandan NVQF Level aware logic
    nvqf_level = str(kwargs.get('level', '4'))
    selected_levels = ["Remember", "Understand", "Apply"] # Default Level 3
    
    if "5" in nvqf_level: # Higher order thinking for Level 5
        selected_levels = ["Analyze", "Evaluate", "Create"]
    elif "4" in nvqf_level: # Intermediate
        selected_levels = ["Understand", "Apply", "Analyze"]
    
    # Template overrides for focus
    if "theory" in template_type.lower() and "5" in nvqf_level:
        selected_levels = ["Analyze", "Evaluate", "Understand"]
    elif "practical" in template_type.lower() and "5" in nvqf_level:
        selected_levels = ["Create", "Apply", "Analyze"]
        
    verbs = []
    import random
    for level in selected_levels:
        verbs.append(random.choice(blooms_verbs[level]))

    # Construct the SMART objectives using the stem
    objective_items = []
    stem = "By the end of this lesson, students will be able to"
    
    # Try to use range_details for specific context if available
    context = kwargs.get('range_details') or topic
    
    objective_items.append(f"1. {stem} {verbs[0]} the key principles of {topic}.")
    objective_items.append(f"2. {stem} {verbs[1]} {context} in professional scenarios.")
    objective_items.append(f"3. {stem} {verbs[2]} the outcomes related to {topic} effectively with a professional attitude.")

    objectives_text = "\n".join(objective_items)

    # Aggregate plan data
    plan_data = {
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
        "pre_requisite_knowledge": kwargs.get('pre_requisite_knowledge', 'Basic understanding of the previous competency level.'),
        "cross_cutting_issues": cross_cutting,
        "hse_considerations": hse_text,
        "ict_tools": ict_tools,
        "special_needs_support": special_needs,
        "topic": topic,
        "objectives": objectives_text,
        "facilitation_technique": technique,
        "resources": final_resources,
        "indicative_content": kwargs.get('indicative_content', 'Detailed content from syllabus.'),
        "range_details": context,
        "duration": f"{total_minutes} min",
        "reflection": "Session conducted successfully. Learners were engaged in the groups and showed understanding through assessment.",
        "activities": activities
    }
    
    return plan_data
