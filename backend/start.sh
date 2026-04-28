#!/bin/bash
# Startup script for Render - force-seed and start server

echo "Running migrations..."
python manage.py migrate

echo "Force-seeding merchants with correct UUIDs..."
python force_seed.py

echo "Starting gunicorn..."
gunicorn playto.wsgi:application

