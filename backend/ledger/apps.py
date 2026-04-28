from django.apps import AppConfig


class LedgerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ledger'

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') or os.environ.get('GUNICORN_CMD_ARGS'):
            self._auto_seed()

    def _auto_seed(self):
        from django.db.utils import OperationalError, ProgrammingError
        try:
            from .models import Merchant, Transaction
            from django.db import connection

            # Check if already seeded
            if Merchant.objects.exists():
                return

            merchants_data = [
                ('Rahul Designs', 'rahul@designs.in', [
                    (2500000, 'Payment from US client #1'),
                    (1500000, 'Payment from UK client #2'),
                    (1000000, 'Payment from EU client #3'),
                ]),
                ('Priya Tech Solutions', 'priya@tech.in', [
                    (2500000, 'SaaS subscription payment'),
                ]),
                ('Amit Studio', 'amit@studio.in', [
                    (5000000, 'Video production advance'),
                    (2500000, 'Final delivery payment'),
                ]),
            ]

            for name, email, credits in merchants_data:
                merchant, _ = Merchant.objects.get_or_create(
                    email=email,
                    defaults={'name': name}
                )
                for amount, desc in credits:
                    Transaction.objects.get_or_create(
                        merchant=merchant,
                        amount_paise=amount,
                        type=Transaction.CREDIT,
                        description=desc
                    )

            print("Auto-seeded merchants and transactions.")
        except (OperationalError, ProgrammingError):
            # DB not ready yet, skip
            pass
