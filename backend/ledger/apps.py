from django.apps import AppConfig
import uuid


class LedgerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ledger'

    def ready(self):
        self._auto_seed()

    def _auto_seed(self):
        from django.db.utils import OperationalError, ProgrammingError
        try:
            from .models import Merchant, Transaction

            # Check if already seeded
            if Merchant.objects.exists():
                return

            # Fixed UUIDs matching frontend dropdown
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
                merchant, created = Merchant.objects.get_or_create(
                    id=data['id'],
                    defaults={
                        'name': data['name'],
                        'email': data['email']
                    }
                )
                if not created:
                    merchant.name = data['name']
                    merchant.email = data['email']
                    merchant.save()

                # Clear existing transactions for clean seed
                Transaction.objects.filter(merchant=merchant).delete()

                for amount, desc in data['credits']:
                    Transaction.objects.create(
                        merchant=merchant,
                        amount_paise=amount,
                        type=Transaction.CREDIT,
                        description=desc
                    )

            print("Auto-seeded merchants and transactions.")
        except (OperationalError, ProgrammingError):
            # DB not ready yet, skip
            pass
