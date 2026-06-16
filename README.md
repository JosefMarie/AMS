# Academic Management System (AMS)

A web-based Academic Management System built with Django, tailored for managing session plans, student tracking, AI-powered content generation, and school collaboration.

## Features
- **User Roles**: Admin, Teacher, Student with distinct personas and permission levels.
- **Digital ID Cards**: Premium 3D flip-effect digital ID cards for Students and Trainers, featuring responsive glassmorphic geometric poly backgrounds.
- **Credential Verification System**: Automatically generated QR codes on the back of Digital IDs linking to a public, secure verification portal.
- **Session & Scheme of Work Generators**: Create and export "Delivering" and "Practical" session plans (PDF) or generate comprehensive Schemes of Work using the integrated AI Education Assistant.
- **Student Tracker & Gradebook**: Interactive, spreadsheet-like gradebook and robust attendance tracking.
- **Co-Teaching & Classroom Sharing**: Robust permission system allowing trainers to request co-teacher access and collaborate on shared classrooms.
- **Timetable UI**: Advanced interactive timetable interface.
- **AI Quiz Module**: Generate dynamic quizzes from syllabus content.

## Tech Stack
-   **Backend**: Django (Python)
-   **Database**: SQLite (Development)
-   **Frontend**: Tailwind CSS, HTML5, Vanilla JavaScript
-   **PDF Generation**: WeasyPrint
-   **QR Generation**: QRious.js

## Setup Instructions

1.  **Clone/Download the repository**.
2.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run Migrations**:
    ```bash
    python manage.py migrate
    ```
5.  **Create Superuser**:
    ```bash
    python manage.py createsuperuser
    ```
6.  **Run Server**:
    ```bash
    python manage.py runserver
    ```

## Project Structure
-   `ams_project/`: Django project settings.
-   `core/`: Main functionality (Models, Views, Forms, APIs).
-   `templates/`: HTML Templates (Tailwind-styled).
-   `static/`: Custom CSS, JS plugins, Images.
