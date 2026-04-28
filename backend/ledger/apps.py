from django.apps import AppConfig
import uuid
import time
import sys


class LedgerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ledger'

    # Fixed UUIDs matching frontend dropdown
    FIXED_UIDS = [
        uuid.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'),
        uuid.UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890'),
        uuid.UUID('5a6b7c8d-9e0f-1234-5678-9abcdef01234'),
    ]

    def ready(self):
        """Run seed on startup - simplified to always run."""
        if 'runserver' in sys.argv or any('gunicorn' in arg for arg in sys.argv):
            self._force_seed()

    def _force_seed(self):
        """Delete all merchants and re-seed with correct UUIDs."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from .models import Merchant, Transaction
                import traceback

                print(f"[Auto-seed] Attempt {attempt + 1}: Force seeding...")

                # Delete ALL existing merchants (this will cascade to transactions)
                merchant_count = Merchant.objects.count()
                print(f"[Auto-seed] Found {merchant_count} existing merchants, deleting all...")

                # Delete in correct order to avoid FK issues
                Transaction.objects.all().delete()
                Merchant.objects.all().delete()

                print("[Auto-seed] Cleared existing data, creating new merchants...")

                # Create merchants with FIXED UUIDs
                merchants_data = [
                    {
                        'id': LedgerConfig.FIXED_UIDS[0],
                        'name': 'Rahul Designs',
                        'email': 'rahul@designs.in',
                        'credits': [
                            (2500000, 'Payment from US client #1'),
                            (1500000, 'Payment from UK client #2'),
                            (1000000, 'Payment from EU client #3'),
                        ]
                    },
                    {
                        'id': LedgerConfig.FIXED_UIDS[1],
                        'name': 'Priya Tech Solutions',
                        'email': 'priya@tech.in',
                        'credits': [
                            (2500000, 'SaaS subscription payment'),
                        ]
                    },
                    {
                        'id': LedgerConfig.FIXED_UIDS[2],
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
                    print(f"[Auto-seed] Created merchant: {data['name']} ({data['id']})")

                    for amount, desc in data['credits']:
                        Transaction.objects.create(
                            merchant=merchant,
                            amount_paise=amount,
                            type=Transaction.CREDIT,
                            description=desc
                        )

                print("[Auto-seed] Done! Seeded 3 merchants with FIXED UUIDs.")
                return

            except Exception as e:
                print(f"[Auto-seed] Attempt {attempt + 1} failed: {e}")
                traceback.print_exc()
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print("[Auto-seed] All attempts failed. Check logs!")
