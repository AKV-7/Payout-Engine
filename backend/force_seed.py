#!/usr/bin/env python
"""Force-seed merchants with correct UUIDs. Called from start.sh."""
import os
import django
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playto.settings")
django.setup()

from ledger.models import Merchant, Transaction

FIXED_UUIDS = [
    uuid.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'),
    uuid.UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890'),
    uuid.UUID('5a6b7c8d-9e0f-1234-5678-9abcdef01234'),
]

def force_seed():
    print("[Seed Script] Force seeding merchants with correct UUIDs...")
    
    # Delete ALL existing merchants (cascades to transactions)
    count = Merchant.objects.count()
    print(f"[Seed Script] Found {count} existing merchants, deleting all...")
    Merchant.objects.all().delete()
    Transaction.objects.all().delete()
    
    # Create merchants with FIXED UUIDs
    merchants_data = [
        {
            'id': FIXED_UUIDS[0],
            'name': 'Rahul Designs',
            'email': 'rahul@designs.in',
            'credits': [
                (2500000, 'Payment from US client #1'),
                (1500000, 'Payment from UK client #2'),
                (1000000, 'Payment from EU client #3'),
            ]
        },
        {
            'id': FIXED_UUIDS[1],
            'name': 'Priya Tech Solutions',
            'email': 'priya@tech.in',
            'credits': [
                (2500000, 'SaaS subscription payment'),
            ]
        },
        {
            'id': FIXED_UUIDS[2],
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
        print(f"[Seed Script] Created merchant: {data['name']} ({data['id']})")
        
        for amount, desc in data['credits']:
            Transaction.objects.create(
                merchant=merchant,
                amount_paise=amount,
                type=Transaction.CREDIT,
                description=desc
            )
    
    print("[Seed Script] Done! Seeded 3 merchants with correct UUIDs.")

if __name__ == '__main__':
    force_seed()
