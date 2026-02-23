# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for WeasyPrint and Postgres
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg2-binary

# Copy the current directory contents into the container at /app
COPY . /app/

# Run collectstatic
RUN python manage.py collectstatic --noinput

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "ams_project.wsgi:application"]
