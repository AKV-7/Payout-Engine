#!/bin/bash
# Startup script for Render - runs migrations and starts server

echo "Running migrations..."
python manage.py migrate

echo "Starting gunicorn..."
gunicorn playto.wsgi:application
