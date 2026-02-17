# AI Quiz Generation Helper
# This module integrates with Google Gemini AI to generate quiz questions

import google.generativeai as genai
import json
import random
import os

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyD2RDTdZHD4Fxn-3pNDT9LeWVSS0-UQm_c"

def generate_quiz_with_ai(syllabus_content, num_mcq=10, num_tf=5, num_matching=5):
    """
    Generate quiz questions using Google Gemini AI based on syllabus content.
    
    Args:
        syllabus_content (str): The syllabus text to analyze
        num_mcq (int): Number of multiple choice questions
        num_tf (int): Number of true/false questions
        num_matching (int): Number of matching pairs
    
    Returns:
        dict: Quiz data with mcq, true_false, and matching questions
    """
    
    if not GEMINI_API_KEY:
        # Fallback to sample data if no API key
        return generate_sample_quiz(num_mcq, num_tf, num_matching)
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
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
        
        response = model.generate_content(prompt)
        quiz_data = json.loads(response.text.strip())
        
        # Shuffle matching questions
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
