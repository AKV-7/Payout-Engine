#!/bin/bash
echo "Running migrations..."
python manage.py migrate

echo "Force-seeding merchants..."
python force_seed.py

echo "Starting gunicorn..."
exec gunicorn playto.wsgi:application
