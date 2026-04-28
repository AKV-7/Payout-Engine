import uuid
import threading
import time
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import (
    Merchant, Transaction, Payout, IdempotencyRecord,
    get_balance, get_held_balance,
)


class ConcurrencyTest(TransactionTestCase):
    """
    Test that two simultaneous payout requests for the same merchant
    cannot both succeed if the balance is insufficient for both.
    """

    def test_simultaneous_payouts_prevent_overdraft(self):
        merchant = Merchant.objects.create(
            name='Test Merchant',
            email='test@example.com'
        )
        # Seed 100 rupees = 10000 paise
        Transaction.objects.create(
            merchant=merchant,
            amount_paise=10000,
            type=Transaction.CREDIT,
            description='Seed credit'
        )

        results = []
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        def request_payout(key):
            client = APIClient()
            response = client.post(
                reverse('payout-list-create'),
                data={
                    'amount_paise': 6000,
                    'bank_account_id': 'BANK123'
                },
                headers={
                    'X-Merchant-ID': str(merchant.id),
                    'Idempotency-Key': key,
                }
            )
            results.append({
                'status': response.status_code,
                'key': key,
                'data': response.data
            })

        t1 = threading.Thread(target=request_payout, args=(key1,))
        t2 = threading.Thread(target=request_payout, args=(key2,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = [r for r in results if r['status'] == 201]
        failures = [r for r in results if r['status'] == 400]

        # Exactly one should succeed, one should be rejected
        self.assertEqual(len(successes), 1, f"Expected 1 success, got {len(successes)}: {results}")
        self.assertEqual(len(failures), 1, f"Expected 1 failure, got {len(failures)}: {results}")

        # Only one payout should exist
        self.assertEqual(Payout.objects.count(), 1)

        # Verify ledger integrity: credits - debits should equal balance
        # No debits yet because payout is still pending
        balance = get_balance(merchant.id)
        self.assertEqual(balance, 10000)

        # Held balance should be 6000
        held = get_held_balance(merchant.id)
        self.assertEqual(held, 6000)

        # Available should be 4000
        self.assertEqual(balance - held, 4000)


class IdempotencyTest(TestCase):
    """
    Test that duplicate requests with the same idempotency key
    return the same response without creating duplicate payouts.
    """

    def setUp(self):
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            email='test2@example.com'
        )
        Transaction.objects.create(
            merchant=self.merchant,
            amount_paise=50000,
            type=Transaction.CREDIT,
            description='Seed credit'
        )
        self.client = APIClient()
        self.key = str(uuid.uuid4())

    def test_duplicate_idempotency_key_returns_same_response(self):
        # First request
        resp1 = self.client.post(
            reverse('payout-list-create'),
            data={
                'amount_paise': 10000,
                'bank_account_id': 'BANK456'
            },
            headers={
                'X-Merchant-ID': str(self.merchant.id),
                'Idempotency-Key': self.key,
            }
        )
        self.assertEqual(resp1.status_code, 201)
        payout_id_1 = resp1.data['id']

        # Second request with same key
        resp2 = self.client.post(
            reverse('payout-list-create'),
            data={
                'amount_paise': 10000,
                'bank_account_id': 'BANK456'
            },
            headers={
                'X-Merchant-ID': str(self.merchant.id),
                'Idempotency-Key': self.key,
            }
        )
        self.assertEqual(resp2.status_code, 200)
        payout_id_2 = resp2.data['id']

        # Same payout returned
        self.assertEqual(payout_id_1, payout_id_2)

        # Only one payout exists
        self.assertEqual(Payout.objects.count(), 1)

        # Only one idempotency record
        self.assertEqual(IdempotencyRecord.objects.count(), 1)

    def test_same_key_different_payload_returns_409(self):
        # First request
        resp1 = self.client.post(
            reverse('payout-list-create'),
            data={
                'amount_paise': 10000,
                'bank_account_id': 'BANK456'
            },
            headers={
                'X-Merchant-ID': str(self.merchant.id),
                'Idempotency-Key': self.key,
            }
        )
        self.assertEqual(resp1.status_code, 201)

        # Second request with same key but different amount
        resp2 = self.client.post(
            reverse('payout-list-create'),
            data={
                'amount_paise': 20000,
                'bank_account_id': 'BANK456'
            },
            headers={
                'X-Merchant-ID': str(self.merchant.id),
                'Idempotency-Key': self.key,
            }
        )
        self.assertEqual(resp2.status_code, 409)

        # Still only one payout
        self.assertEqual(Payout.objects.count(), 1)


class StateMachineTest(TestCase):
    """Test that illegal state transitions are blocked."""

    def test_failed_to_completed_blocked(self):
        merchant = Merchant.objects.create(name='SM Test', email='sm@test.com')
        payout = Payout.objects.create(
            merchant=merchant,
            amount_paise=1000,
            bank_account_id='BANK',
            status=Payout.FAILED,
            idempotency_key=uuid.uuid4()
        )

        from .models import InvalidStateTransition
        with self.assertRaises(InvalidStateTransition):
            payout.transition_to(Payout.COMPLETED)

    def test_completed_to_any_blocked(self):
        merchant = Merchant.objects.create(name='SM Test2', email='sm2@test.com')
        payout = Payout.objects.create(
            merchant=merchant,
            amount_paise=1000,
            bank_account_id='BANK',
            status=Payout.COMPLETED,
            idempotency_key=uuid.uuid4()
        )

        from .models import InvalidStateTransition
        with self.assertRaises(InvalidStateTransition):
            payout.transition_to(Payout.PENDING)

        with self.assertRaises(InvalidStateTransition):
            payout.transition_to(Payout.FAILED)
