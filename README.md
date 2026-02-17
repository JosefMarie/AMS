# Academic Management System (AMS)

A web-based Academic Management System built with Django, tailored for managing session plans, student tracking, and automated quiz generation.

## Features
- **User Roles**: Admin, Teacher, Student.
- **Session Plan Generator**: Create and export "Delivering" and "Practical" session plans (PDF).
- **Student Tracker**: simple Gradebook and Attendance tracking.
- **AI Quiz Module**: Generate quizzes from syllabus content (Stub/Mock initially).

## Tech Stack
-   **Backend**: Django (Python)
-   **Database**: SQLite (Development)
-   **Frontend**: Tailwind CSS, HTML5, JavaScript
-   **PDF Generation**: WeasyPrint

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
-   `core/`: Main functionality (Models, Views, Forms).
-   `templates/`: HTML Templates.
-   `static/`: CSS (Tailwind), JS, Images.
