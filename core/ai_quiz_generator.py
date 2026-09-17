# AI Quiz Generation Helper
# This module integrates with Google Gemini AI to generate quiz questions

from google import genai
import json
import random
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


# ─────────────────────────────────────────────────────────────────────────────
# Strategy D: Per-User API Key Resolution
# Priority: user's personal key → env var → global SystemSetting key
# ─────────────────────────────────────────────────────────────────────────────
def get_api_key(user=None):
    """
    Resolve the best available Gemini API key.
    Priority order:
      1. The requesting user's personal gemini_api_key (Strategy D)
      2. GEMINI_API_KEY environment variable
      3. Global SystemSetting.gemini_api_key from the database
    """
    candidates = get_candidate_api_keys(user=user)
    return candidates[0][1] if candidates else ''


def get_candidate_api_keys(user=None):
    """
    Return candidate Gemini API keys in priority order:
      1. Requesting user's personal gemini_api_key (Strategy D)
      2. GEMINI_API_KEY environment variable
      3. Global SystemSetting.gemini_api_key from database
    Returns a list of tuples: [('personal'|'env'|'system', key_string)]
    """
    candidates = []
    seen = set()

    # 1. User's personal key
    if user is not None:
        try:
            personal_key = (getattr(user, 'gemini_api_key', '') or '').strip()
            if personal_key and personal_key not in seen:
                candidates.append(('personal', personal_key))
                seen.add(personal_key)
        except Exception:
            pass

    # 2. Environment variable
    env_key = (os.environ.get('GEMINI_API_KEY', '') or '').strip()
    if env_key and env_key not in seen:
        candidates.append(('env', env_key))
        seen.add(env_key)

    # 3. Global database setting
    try:
        from .models import SystemSetting
        db_key = (SystemSetting.get_settings().gemini_api_key or '').strip()
        if db_key and db_key not in seen:
            candidates.append(('system', db_key))
            seen.add(db_key)
    except Exception:
        pass

    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# Strategy B: Exponential Backoff Retry Wrapper
# Automatically retries on 429 (quota exceeded) and 503 (server overload)
# ─────────────────────────────────────────────────────────────────────────────
def gemini_call_with_retry(client, model, contents, max_retries=4, initial_delay=2, **kwargs):
    """
    Call client.models.generate_content() with exponential backoff retry.

    Retries on:
      - 429 Resource Exhausted (rate limit hit)
      - 503 Service Unavailable (server overloaded)

    Args:
        client:         An initialised genai.Client instance.
        model:          Model name string e.g. 'gemini-3.6-flash'.
        contents:       The prompt / contents payload.
        max_retries:    Maximum number of attempts (default 4 → up to ~30 s wait).
        initial_delay:  Seconds to wait before first retry (doubles each attempt).
        kwargs:         Extra parameters passed directly to generate_content (e.g. config).

    Returns:
        The Gemini response object.

    Raises:
        The last exception if all retries are exhausted.
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            return client.models.generate_content(model=model, contents=contents, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            # Retry on quota / overload errors only
            if any(code in err_str for code in ['429', '503', 'resource_exhausted',
                                                  'quota', 'too many requests',
                                                  'unavailable', 'overloaded']):
                last_error = e
                if attempt < max_retries - 1:
                    wait = delay * (2 ** attempt)   # 2s, 4s, 8s, 16s …
                    print(f"[Gemini] Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                          f"Retrying in {wait}s…")
                    time.sleep(wait)
                    continue
            # Non-retryable error — raise immediately
            raise

    raise last_error


def gemini_call_with_key_fallback(contents, model='gemini-3.6-flash', user=None, max_retries=4, initial_delay=2, **kwargs):
    """
    Execute a Gemini generate_content call using the best available key,
    automatically falling back to secondary keys (e.g. system/env key) if the primary
    key fails due to authentication (401/400) or exhausted quota (429).
    """
    candidates = get_candidate_api_keys(user=user)
    if not candidates:
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in .env or System Settings.")

    last_error = None
    for idx, (key_type, key) in enumerate(candidates):
        try:
            client = genai.Client(api_key=key)
            return gemini_call_with_retry(
                client,
                model=model,
                contents=contents,
                max_retries=max_retries,
                initial_delay=initial_delay,
                **kwargs
            )
        except Exception as e:
            err_str = str(e).lower()
            # Check if this error is an auth failure or quota depletion
            is_recoverable_with_fallback = any(term in err_str for term in [
                '401', 'unauthenticated', 'invalid authentication',
                'access_token_type_unsupported', '400', 'invalid_argument',
                'api key not valid', '429', 'resource_exhausted',
                'prepayment credits are depleted'
            ])

            has_fallback = idx < len(candidates) - 1
            if is_recoverable_with_fallback and has_fallback:
                print(f"[Gemini] Candidate key ({key_type}) failed with: {e}. Falling back to next available key...")
                # If personal key was unauthenticated/invalid, clear it from user
                if key_type == 'personal' and user:
                    if any(t in err_str for t in ['401', 'unauthenticated', 'invalid_argument', 'api key not valid', 'access_token_type_unsupported']):
                        try:
                            user.gemini_api_key = ''
                            user.save(update_fields=['gemini_api_key'])
                            print(f"[Gemini] Auto-cleared invalid personal API key for user {getattr(user, 'username', '')}.")
                        except Exception:
                            pass
                last_error = e
                continue
            raise

    raise last_error


# ─────────────────────────────────────────────────────────────────────────────
# Quiz Generation
# ─────────────────────────────────────────────────────────────────────────────
def generate_quiz_with_ai(syllabus_content, num_mcq=10, num_tf=5, num_matching=5, user=None):
    """
    Generate quiz questions using Google Gemini AI based on syllabus content.

    Args:
        syllabus_content (str): The syllabus text to analyze.
        num_mcq (int):          Number of multiple-choice questions.
        num_tf (int):           Number of true/false questions.
        num_matching (int):     Number of matching pairs.
        user:                   Optional Django user for per-user key (Strategy D).

    Returns:
        dict: Quiz data with mcq, true_false, and matching questions.
    """
    candidates = get_candidate_api_keys(user=user)
    if not candidates:
        return generate_sample_quiz(num_mcq, num_tf, num_matching)

    try:
        prompt = f"""Based on the following syllabus content, generate a quiz with:
- {num_mcq} multiple choice questions (4 options each)
- {num_tf} true/false questions
- {num_matching} matching pairs (term and definition)

Syllabus Content:
{syllabus_content}

Generate questions that test understanding of key concepts, definitions, and relationships in the content.
Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
    "mcq": [
        {{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A"}}
    ],
    "true_false": [
        {{"question": "...", "answer": "True"}}
    ],
    "matching": [
        {{"term": "...", "definition": "..."}}
    ]
}}"""

        response = gemini_call_with_key_fallback(prompt, model='gemini-3.6-flash', user=user)
        quiz_data = json.loads(response.text.strip())

        if 'matching' in quiz_data and quiz_data['matching']:
            random.shuffle(quiz_data['matching'])

        return quiz_data

    except Exception as e:
        print(f"AI generation error: {e}")
        return generate_sample_quiz(num_mcq, num_tf, num_matching)


def generate_sample_quiz(num_mcq=10, num_tf=5, num_matching=5):
    """Generate sample quiz data when AI is unavailable."""
    return {
        'mcq': [
            {
                'question': f'Sample MCQ question {i+1} based on syllabus content',
                'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                'answer': 'Option A'
            } for i in range(num_mcq)
        ],
        'true_false': [
            {'question': f'Sample T/F question {i+1}', 'answer': random.choice(['True', 'False'])}
            for i in range(num_tf)
        ],
        'matching': [
            {'term': f'Term {i+1}', 'definition': f'Definition for term {i+1}'}
            for i in range(num_matching)
        ]
    }
