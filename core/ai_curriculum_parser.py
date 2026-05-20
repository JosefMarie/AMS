import google.generativeai as genai
import json
import os
import time
from .ai_quiz_generator import get_api_key
from .models import SyllabusModule, LearningOutcome, IndicativeContent, Topic

def parse_curriculum_pdf(curriculum):
    """
    Uploads a Curriculum PDF to Gemini, extracts the TVET hierarchy, and saves it to the database.
    """
    api_key = get_api_key()
    if not api_key:
        raise Exception("Gemini API key is missing. Please add it in System Settings.")
    
    genai.configure(api_key=api_key)
    
    if not curriculum.pdf_document:
        raise Exception("Curriculum does not have a PDF document attached.")
        
    pdf_path = curriculum.pdf_document.path
    if not os.path.exists(pdf_path):
        raise Exception("PDF file not found on disk.")

    # Upload to Gemini File API
    print(f"Uploading {pdf_path} to Gemini...")
    uploaded_file = genai.upload_file(pdf_path, mime_type="application/pdf")
    
    # Wait for processing if needed (though PDFs usually process quickly)
    while uploaded_file.state.name == 'PROCESSING':
        print("Waiting for file processing...")
        time.sleep(2)
        uploaded_file = genai.get_file(uploaded_file.name)
        
    if uploaded_file.state.name == 'FAILED':
        raise Exception("Failed to process the PDF in Gemini.")

    prompt = """
    You are an expert TVET Curriculum Data Extractor. 
    Analyze the attached curriculum/syllabus PDF document and extract the hierarchy exactly as requested.
    I need you to output valid JSON ONLY, representing the structural hierarchy of the curriculum.

    The hierarchy is:
    Modules -> Learning Outcomes (LO) -> Indicative Content (IC) -> Topics

    Output format MUST be strictly:
    {
        "modules": [
            {
                "code": "e.g., ICT SDV 4 01",
                "title": "e.g., Develop Web Applications",
                "learning_outcomes": [
                    {
                        "title": "e.g., LO1: Analyze requirements",
                        "indicative_contents": [
                            {
                                "title": "e.g., IC1: Requirement gathering",
                                "topics": [
                                    "Functional requirements",
                                    "Non-functional requirements"
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    Do not use markdown blocks like ```json. Just return the raw JSON text.
    Extract as many modules as you can clearly identify. Keep titles concise but descriptive.
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("Extracting data with Gemini 2.5 Flash...")
    response = model.generate_content([uploaded_file, prompt])
    
    # Cleanup file
    try:
        genai.delete_file(uploaded_file.name)
    except:
        pass
        
    response_text = response.text.strip()
    # Remove markdown formatting if the AI ignores instructions
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
        
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        print("Raw response:", response.text)
        raise Exception("AI did not return valid JSON. Extraction failed.")
        
    # Programmatically create the DB objects
    if 'modules' not in data:
        raise Exception("JSON missing 'modules' key.")
        
    # Clear existing modules to avoid duplicates if re-running
    SyllabusModule.objects.filter(curriculum=curriculum).delete()
    
    modules_created = 0
    for mod_data in data['modules']:
        module = SyllabusModule.objects.create(
            curriculum=curriculum,
            code=mod_data.get('code', 'UNKNOWN'),
            title=mod_data.get('title', 'Untitled Module')
        )
        modules_created += 1
        
        for lo_data in mod_data.get('learning_outcomes', []):
            lo = LearningOutcome.objects.create(
                module=module,
                title=lo_data.get('title', 'Untitled LO')
            )
            
            for ic_data in lo_data.get('indicative_contents', []):
                ic = IndicativeContent.objects.create(
                    learning_outcome=lo,
                    title=ic_data.get('title', 'Untitled IC')
                )
                
                for topic_str in ic_data.get('topics', []):
                    Topic.objects.create(
                        indicative_content=ic,
                        title=str(topic_str)
                    )
                    
    return modules_created
