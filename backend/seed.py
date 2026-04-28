#!/usr/bin/env python
"""
Seed script to populate test merchants with credit history.
Run with: python seed.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playto.settings")
django.setup()

from ledger.models import Merchant, Transaction


def seed():
    print("Seeding merchants...")

    m1, _ = Merchant.objects.get_or_create(
        email="rahul@designs.in",
        defaults={"name": "Rahul Designs"}
    )
    m2, _ = Merchant.objects.get_or_create(
        email="priya@tech.in",
        defaults={"name": "Priya Tech Solutions"}
    )
    m3, _ = Merchant.objects.get_or_create(
        email="amit@studio.in",
        defaults={"name": "Amit Studio"}
    )

    # Clear existing transactions for clean seed
    Transaction.objects.filter(merchant__in=[m1, m2, m3]).delete()

    # Merchant 1: Rahul Designs - 50,000 INR in credits
    Transaction.objects.create(
        merchant=m1,
        amount_paise=25_000_00,
        type=Transaction.CREDIT,
        description="Payment from US client #1"
    )
    Transaction.objects.create(
        merchant=m1,
        amount_paise=15_000_00,
        type=Transaction.CREDIT,
        description="Payment from UK client #2"
    )
    Transaction.objects.create(
        merchant=m1,
        amount_paise=10_000_00,
        type=Transaction.CREDIT,
        description="Payment from EU client #3"
    )

    # Merchant 2: Priya Tech - 25,000 INR in credits
    Transaction.objects.create(
        merchant=m2,
        amount_paise=25_000_00,
        type=Transaction.CREDIT,
        description="SaaS subscription payment"
    )

    # Merchant 3: Amit Studio - 75,000 INR in credits
    Transaction.objects.create(
        merchant=m3,
        amount_paise=50_000_00,
        type=Transaction.CREDIT,
        description="Video production advance"
    )
    Transaction.objects.create(
        merchant=m3,
        amount_paise=25_000_00,
        type=Transaction.CREDIT,
        description="Final delivery payment"
    )

    print("\n=== Seeded Merchants ===")
    for m in [m1, m2, m3]:
        from ledger.models import get_balance
        bal = get_balance(m.id)
        print(f"{m.name} ({m.id})")
        print(f"  Email: {m.email}")
        print(f"  Balance: INR {bal / 100:,.2f}")
        print()

    print("Done! Use the Merchant ID above in the dashboard.")


if __name__ == "__main__":
    seed()
