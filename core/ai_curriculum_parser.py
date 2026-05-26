from google import genai
from google.genai import types
import json
import os
import time
from .ai_quiz_generator import get_api_key, gemini_call_with_retry
from .models import SyllabusModule, LearningOutcome, IndicativeContent, Topic

def parse_curriculum_pdf(curriculum, user=None):
    """
    Uploads a Curriculum PDF to Gemini, extracts the TVET hierarchy, and saves it to the database.
    Supports Strategies B (retry helper), D (personal keys), and E (explicit Context Caching).
    """
    api_key = get_api_key(user=user)
    if not api_key:
        raise Exception("Gemini API key is missing. Please add it in System Settings or your Profile.")

    client = genai.Client(api_key=api_key)

    if not curriculum.pdf_document:
        raise Exception("Curriculum does not have a PDF document attached.")

    pdf_path = curriculum.pdf_document.path
    if not os.path.exists(pdf_path):
        raise Exception("PDF file not found on disk.")

    # Upload to Gemini File API
    print(f"Uploading {pdf_path} to Gemini...")
    with open(pdf_path, 'rb') as f:
        uploaded_file = client.files.upload(
            file=f,
            config=types.UploadFileConfig(mime_type="application/pdf")
        )

    # Wait for processing if needed
    while uploaded_file.state and uploaded_file.state.name == 'PROCESSING':
        print("Waiting for file processing...")
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state and uploaded_file.state.name == 'FAILED':
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
                "hours": 100,
                "credits": 10,
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

    # Strategy E: Explicit Context Caching for large syllabus files
    cache = None
    try:
        print("Creating Context Cache for syllabus PDF...")
        cache = client.caches.create(
            model='gemini-2.5-flash',
            config=types.CreateCachedContentConfig(
                display_name=f"curriculum_pdf_{curriculum.id}",
                contents=[uploaded_file],
                ttl="300s"  # 5 minutes TTL
            )
        )
        print(f"Context cache successfully created: {cache.name}")
    except Exception as cache_err:
        print(f"Context cache creation bypassed/failed ({cache_err}). Continuing without cache.")

    print("Extracting data with Gemini 2.5 Flash...")
    if cache:
        response = gemini_call_with_retry(
            client,
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                cached_content=cache.name
            )
        )
    else:
        response = gemini_call_with_retry(
            client,
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_uri(file_uri=uploaded_file.uri, mime_type="application/pdf"),
                prompt
            ]
        )

    # Cleanup file & cache if possible
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass
    if cache:
        try:
            client.caches.delete(name=cache.name)
        except Exception:
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
    except json.JSONDecodeError:
        print("Raw response:", response.text)
        raise Exception("AI did not return valid JSON. Extraction failed.")

    # Programmatically create the DB objects
    if 'modules' not in data:
        raise Exception("JSON missing 'modules' key.")

    # Clear existing modules to avoid duplicates if re-running
    SyllabusModule.objects.filter(curriculum=curriculum).delete()

    modules_created = 0
    for mod_data in data['modules']:
        # Extract hours and credits safely
        raw_hours = mod_data.get('hours', 100)
        raw_credits = mod_data.get('credits', 10)
        try:
            hours_val = int(raw_hours) if raw_hours else 100
        except (ValueError, TypeError):
            hours_val = 100
        try:
            credits_val = int(raw_credits) if raw_credits else 10
        except (ValueError, TypeError):
            credits_val = 10

        module = SyllabusModule.objects.create(
            curriculum=curriculum,
            code=mod_data.get('code', 'UNKNOWN'),
            title=mod_data.get('title', 'Untitled Module'),
            hours=hours_val,
            credits=credits_val
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
