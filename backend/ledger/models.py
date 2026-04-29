import uuid
import hashlib
from django.db import models, transaction
from django.db.models import Sum, Q, F
from django.core.exceptions import ValidationError
from django.utils import timezone


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'merchants'

    def __str__(self):
        return self.name


class Transaction(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'
    TYPE_CHOICES = [(CREDIT, 'Credit'), (DEBIT, 'Debit')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='transactions',
        db_index=True
    )
    amount_paise = models.BigIntegerField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']

    def clean(self):
        if self.amount_paise <= 0:
            raise ValidationError('Amount must be positive')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Payout(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]

    VALID_TRANSITIONS = {
        PENDING: [PROCESSING, FAILED],
        PROCESSING: [COMPLETED, FAILED],
        COMPLETED: [],
        FAILED: [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.PROTECT,
        related_name='payouts',
        db_index=True
    )
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True
    )
    idempotency_key = models.UUIDField()
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payouts'
        unique_together = [['merchant', 'idempotency_key']]
        ordering = ['-created_at']

    def transition_to(self, new_status):
        if new_status not in self.VALID_TRANSITIONS[self.status]:
            raise InvalidStateTransition(
                f"Cannot transition from {self.status} to {new_status}"
            )
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])


class IdempotencyRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='idempotency_records'
    )
    key = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'idempotency_records'
        unique_together = [['merchant', 'key']]


class InvalidStateTransition(Exception):
    pass


class InsufficientFunds(Exception):
    pass


# --- Ledger helpers ---

def get_balance(merchant_id):
    """
    Single-query balance calculation using database-level aggregation.
    No Python arithmetic on fetched rows. No race condition between credit/debit sums.
    """
    result = Transaction.objects.filter(merchant_id=merchant_id).aggregate(
        credits=Sum('amount_paise', filter=Q(type=Transaction.CREDIT)),
        debits=Sum('amount_paise', filter=Q(type=Transaction.DEBIT)),
    )
    credits = result['credits'] or 0
    debits = result['debits'] or 0
    return credits - debits


def get_held_balance(merchant_id):
    """Sum of all payouts in pending or processing state."""
    result = Payout.objects.filter(
        merchant_id=merchant_id,
        status__in=[Payout.PENDING, Payout.PROCESSING]
    ).aggregate(total=Sum('amount_paise'))
    return result['total'] or 0


def hash_payload(body_bytes):
    return hashlib.sha256(body_bytes).hexdigest()
