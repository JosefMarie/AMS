# How to Deploy Your AMS Portal

This guide will show you how to deploy your Django application to **Render.com** (it's the easiest and has a free tier).

## Prerequisites
1.  **GitHub Account**: You need to upload your project to GitHub first.
2.  **Render Account**: Sign up at [render.com](https://render.com).

## Step 1: Push to GitHub
If you haven't already, push your code to a new GitHub repository:
1.  Create a new repository on GitHub.
2.  Run these commands in your project folder (if not already initiated):
    ```bash
    git init
    git add .
    git commit -m "Initial commit for deployment"
    git branch -M main
    git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
    git push -u origin main
    ```

## Step 2: Deploy on Render
1.  Log in to your **Render Dashboard**.
2.  Click **"New +"** and select **"Web Service"**.
3.  Connect your GitHub account and select your repository.
4.   Configure the service:
    *   **Name**: `ams-portal` (or whatever you like)
    *   **Region**: Closest to you (e.g., Frankfurt, Ohio)
    *   **Branch**: `main`
    *   **Runtime**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
    *   **Start Command**: `gunicorn ams_project.wsgi`
    *   **Instance Type**: `Free`

## Step 3: Environment Variables
Still in the Render setup page (or in "Environment" tab later), add these variables:
*   **Key**: `PYTHON_VERSION`, **Value**: `3.12.2`
*   **Key**: `SECRET_KEY`, **Value**: (Generate a random string, e.g., using `openssl rand -hex 32`)
*   **Key**: `DEBUG`, **Value**: `False`
*   **Key**: `ALLOWED_HOSTS`, **Value**: `.onrender.com`

## Step 4: Launch
Click **"Create Web Service"**. Render will start building your app. It might take a few minutes. Check the "Logs" tab to see progress.

Once deployed, Render will give you a URL like `https://ams-portal.onrender.com`.

## Note on Database
This setup uses SQLite, which is fine for a demo/testing but **data will be reset every time the app restarts** on the free tier of Render (because the file system is ephemeral).
If you need persistent data, you should add a **PostgreSQL** database service on Render and configure it (I can help with that if needed).
