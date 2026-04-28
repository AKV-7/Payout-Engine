#!/bin/bash
# Startup script for Render - force-seed and start server

echo "Running migrations..."
python manage.py migrate

echo "Force-seeding merchants with correct UUIDs..."
python manage.py shell <<EOF
from django.db import transaction
from ledger.models import Merchant, Transaction
import uuid

# Delete ALL existing merchants (cascades to transactions)
print("Deleting existing merchants...")
Merchant.objects.all().delete()

# Create merchants with FIXED UUIDs (matching frontend dropdown)
merchants_data = [
    {
        'id': uuid.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'),
        'name': 'Rahul Designs',
        'email': 'rahul@designs.in',
        'credits': [
            (2500000, 'Payment from US client #1'),
            (1500000, 'Payment from UK client #2'),
            (1000000, 'Payment from EU client #3'),
        ]
    },
    {
        'id': uuid.UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890'),
        'name': 'Priya Tech Solutions',
        'email': 'priya@tech.in',
        'credits': [
            (2500000, 'SaaS subscription payment'),
        ]
    },
    {
        'id': uuid.UUID('5a6b7c8d-9e0f-1234-5678-9abcdef01234'),
        'name': 'Amit Studio',
        'email': 'amit@studio.in',
        'credits': [
            (5000000, 'Video production advance'),
            (2500000, 'Final delivery payment'),
        ]
    },
]

for data in merchants_data:
    merchant = Merchant.objects.create(
        id=data['id'],
        name=data['name'],
        email=data['email']
    )
    print(f"Created merchant: {data['name']} ({data['id']})")
    
    for amount, desc in data['credits']:
        Transaction.objects.create(
            merchant=merchant,
            amount_paise=amount,
            type=Transaction.CREDIT,
            description=desc
        )
    print(f"  Added {len(data['credits'])} transactions")

print("Seed complete!")
EOF

echo "Starting gunicorn..."
gunicorn playto.wsgi:application
