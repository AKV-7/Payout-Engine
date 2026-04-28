import uuid
import json
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import (
    Merchant, Transaction, Payout, IdempotencyRecord,
    get_balance, get_held_balance, hash_payload,
    InsufficientFunds, InvalidStateTransition,
)
from .serializers import (
    MerchantSerializer, TransactionSerializer,
    PayoutSerializer, PayoutRequestSerializer,
)
from .tasks import process_payout


class HealthCheckView(generics.APIView):
    def get(self, request, *args, **kwargs):
        return Response({'status': 'ok', 'timestamp': str(timezone.now())})


class DebugMerchantView(generics.APIView):
    def get(self, request, *args, **kwargs):
        try:
            count = Merchant.objects.count()
            merchants = []
            for m in Merchant.objects.all()[:10]:
                merchants.append({
                    'id': str(m.id),
                    'name': m.name,
                    'email': m.email,
                })
            return Response({
                'count': count,
                'merchants': merchants,
            })
        except Exception as e:
            return Response({
                'error': str(e),
                'type': str(type(e).__name__)
            }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            from .apps import LedgerConfig
            LedgerConfig()._auto_seed()
            return Response({'detail': 'Seed triggered'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e),
                'type': str(type(e).__name__)
            }, status=status.HTTP_200_OK)


class MerchantDetailView(generics.RetrieveAPIView):
    serializer_class = MerchantSerializer

    def get_object(self):
        merchant_id = self.request.headers.get('X-Merchant-ID')
        if not merchant_id:
            raise ValidationError({'detail': 'X-Merchant-ID header required'})
        try:
            uuid.UUID(merchant_id)
        except ValueError:
            raise ValidationError({'detail': 'Invalid merchant ID format. Must be a valid UUID.'})
        try:
            return Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            merchants = [{'id': str(m.id), 'name': m.name} for m in Merchant.objects.all()[:5]]
            raise ValidationError({
                'detail': 'Merchant not found',
                'merchant_id': merchant_id,
                'available_merchants': merchants,
                'hint': 'Run POST /api/v1/debug/merchants/ to seed database'
            })


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        merchant_id = self.request.headers.get('X-Merchant-ID')
        if not merchant_id:
            raise ValidationError({'detail': 'X-Merchant-ID header required'})
        try:
            uuid.UUID(merchant_id)
        except ValueError:
            raise ValidationError({'detail': 'Invalid merchant ID format. Must be a valid UUID.'})
        return Transaction.objects.filter(merchant_id=merchant_id)


class PayoutListCreateView(generics.ListCreateAPIView):
    serializer_class = PayoutSerializer

    def get_queryset(self):
        merchant_id = self.request.headers.get('X-Merchant-ID')
        if not merchant_id:
            raise ValidationError({'detail': 'X-Merchant-ID header required'})
        try:
            uuid.UUID(merchant_id)
        except ValueError:
            raise ValidationError({'detail': 'Invalid merchant ID format. Must be a valid UUID.'})
        return Payout.objects.filter(merchant_id=merchant_id)

    def create(self, request, *args, **kwargs):
        merchant_id = request.headers.get('X-Merchant-ID')
        if not merchant_id:
            return Response(
                {'detail': 'X-Merchant-ID header required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            uuid.UUID(merchant_id)
        except ValueError:
            return Response(
                {'detail': 'Invalid merchant ID format. Must be a valid UUID.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'detail': 'Idempotency-Key header required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            idempotency_key = uuid.UUID(idempotency_key)
        except ValueError:
            return Response(
                {'detail': 'Idempotency-Key must be a valid UUID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate body
        req_serializer = PayoutRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount_paise = req_serializer.validated_data['amount_paise']
        bank_account_id = req_serializer.validated_data['bank_account_id']
        payload_bytes = json.dumps(request.data, sort_keys=True).encode()
        payload_hash = hash_payload(payload_bytes)

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response(
                {'detail': 'Merchant not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # --- Idempotency check (fast path, no lock) ---
        try:
            record = IdempotencyRecord.objects.get(
                merchant=merchant,
                key=idempotency_key
            )
            if record.payload_hash != payload_hash:
                return Response(
                    {'detail': 'Idempotency key reused with different payload'},
                    status=status.HTTP_409_CONFLICT
                )
            return Response(record.response_body, status=status.HTTP_200_OK)
        except IdempotencyRecord.DoesNotExist:
            pass

        # --- Core payout creation with pessimistic locking ---
        try:
            with transaction.atomic():
                # Lock merchant row. Any concurrent request for same merchant blocks here.
                merchant = Merchant.objects.select_for_update().get(id=merchant_id)

                # Single-query balance calculation inside the locked transaction
                total_balance = get_balance(merchant.id)
                held_balance = get_held_balance(merchant.id)
                available_balance = total_balance - held_balance

                if available_balance < amount_paise:
                    raise InsufficientFunds(
                        f"Available balance {available_balance} paise is less than "
                        f"requested {amount_paise} paise"
                    )

                # Create payout in pending state
                payout = Payout.objects.create(
                    merchant=merchant,
                    amount_paise=amount_paise,
                    bank_account_id=bank_account_id,
                    status=Payout.PENDING,
                    idempotency_key=idempotency_key,
                )

                # Store idempotency record atomically with payout creation
                response_body = PayoutSerializer(payout).data
                IdempotencyRecord.objects.create(
                    merchant=merchant,
                    key=idempotency_key,
                    payload_hash=payload_hash,
                    response_body=response_body,
                )

        except IntegrityError:
            # Another request won the race and created the idempotency record.
            # Roll back and return the winner's response.
            transaction.set_rollback(True)
            record = IdempotencyRecord.objects.get(
                merchant=merchant,
                key=idempotency_key
            )
            return Response(record.response_body, status=status.HTTP_200_OK)

        except InsufficientFunds as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Queue background worker
        process_payout.delay(str(payout.id))

        return Response(response_body, status=status.HTTP_201_CREATED)


class PayoutDetailView(generics.RetrieveAPIView):
    serializer_class = PayoutSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        merchant_id = self.request.headers.get('X-Merchant-ID')
        if not merchant_id:
            raise ValidationError({'detail': 'X-Merchant-ID header required'})
        try:
            uuid.UUID(merchant_id)
        except ValueError:
            raise ValidationError({'detail': 'Invalid merchant ID format. Must be a valid UUID.'})
        return Payout.objects.filter(merchant_id=merchant_id)
