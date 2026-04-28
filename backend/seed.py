#!/usr/bin/env python
"""
Seed script to populate test merchants with credit history.
Run with: python seed.py
"""
import os
import django
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playto.settings")
django.setup()

from ledger.models import Merchant, Transaction


# Fixed UUIDs so frontend can use them in dropdown
MERCHANTS = {
    "rahul@designs.in": {
        "id": uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "name": "Rahul Designs",
        "credits": [
            (2500000, "Payment from US client #1"),
            (1500000, "Payment from UK client #2"),
            (1000000, "Payment from EU client #3"),
        ]
    },
    "priya@tech.in": {
        "id": uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        "name": "Priya Tech Solutions",
        "credits": [
            (2500000, "SaaS subscription payment"),
        ]
    },
    "amit@studio.in": {
        "id": uuid.UUID("5a6b7c8d-9e0f-1234-5678-9abcdef01234"),
        "name": "Amit Studio",
        "credits": [
            (5000000, "Video production advance"),
            (2500000, "Final delivery payment"),
        ]
    },
}


def seed():
    print("Seeding merchants...")

    for email, data in MERCHANTS.items():
        merchant, created = Merchant.objects.get_or_create(
            id=data["id"],
            defaults={"email": email, "name": data["name"]}
        )
        if not created:
            merchant.email = email
            merchant.name = data["name"]
            merchant.save()

        # Clear existing transactions for clean seed
        Transaction.objects.filter(merchant=merchant).delete()

        # Add credits
        for amount, desc in data["credits"]:
            Transaction.objects.create(
                merchant=merchant,
                amount_paise=amount,
                type=Transaction.CREDIT,
                description=desc
            )
        print(f"  {data['name']} ({merchant.id})")

    print("\n=== Seeded Merchants ===")
    for email, data in MERCHANTS.items():
        from ledger.models import get_balance
        bal = get_balance(data["id"])
        print(f"{data['name']} ({data['id']})")
        print(f"  Email: {email}")
        print(f"  Balance: INR {bal / 100:,.2f}")
        print()

    print("Done! Use the Merchant ID above in the dashboard.")


if __name__ == "__main__":
    seed()
