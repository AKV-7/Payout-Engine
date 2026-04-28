import random
from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .models import Payout, Transaction, IdempotencyRecord


@shared_task(bind=True, max_retries=3)
def process_payout(self, payout_id):
    try:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)

            if payout.status != Payout.PENDING:
                return

            payout.transition_to(Payout.PROCESSING)

        roll = random.random()

        if roll < 0.7:
            with transaction.atomic():
                payout = Payout.objects.select_for_update().get(id=payout_id)
                if payout.status != Payout.PROCESSING:
                    return

                Transaction.objects.create(
                    merchant=payout.merchant,
                    amount_paise=payout.amount_paise,
                    type=Transaction.DEBIT,
                    description=f'Payout settled to {payout.bank_account_id}'
                )

                payout.transition_to(Payout.COMPLETED)
                payout.processed_at = timezone.now()
                payout.save(update_fields=['processed_at'])

        elif roll < 0.9:
            raise self.retry(
                countdown=2 ** self.request.retries * 10,
                exc=Exception('Simulated bank timeout')
            )

        else:
            with transaction.atomic():
                payout = Payout.objects.select_for_update().get(id=payout_id)
                if payout.status != Payout.PROCESSING:
                    return

                payout.transition_to(Payout.FAILED)

    except Exception as exc:
        if self.request.retries >= 3:
            with transaction.atomic():
                try:
                    payout = Payout.objects.select_for_update().get(id=payout_id)
                    if payout.status == Payout.PROCESSING:
                        payout.transition_to(Payout.FAILED)
                except Payout.DoesNotExist:
                    pass
        else:
            raise self.retry(
                exc=exc,
                countdown=2 ** self.request.retries * 10
            )


@shared_task
def retry_stuck_processing():
    cutoff = timezone.now() - timedelta(seconds=30)
    stuck = Payout.objects.filter(
        status=Payout.PROCESSING,
        updated_at__lt=cutoff,
        retry_count__lt=3
    )

    for payout in stuck:
        Payout.objects.filter(id=payout.id).update(
            retry_count=payout.retry_count + 1,
            status=Payout.PENDING
        )
        process_payout.delay(str(payout.id))

    max_retries = Payout.objects.filter(
        status=Payout.PROCESSING,
        updated_at__lt=cutoff,
        retry_count__gte=3
    )
    for payout in max_retries:
        with transaction.atomic():
            locked = Payout.objects.select_for_update().get(id=payout.id)
            if locked.status == Payout.PROCESSING:
                locked.transition_to(Payout.FAILED)


@shared_task
def cleanup_idempotency_keys():
    cutoff = timezone.now() - timedelta(hours=24)
    IdempotencyRecord.objects.filter(created_at__lt=cutoff).delete()
