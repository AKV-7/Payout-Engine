from rest_framework import serializers
from .models import Merchant, Transaction, Payout


class MerchantSerializer(serializers.ModelSerializer):
    available_balance = serializers.SerializerMethodField()
    held_balance = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = ['id', 'name', 'email', 'available_balance', 'held_balance', 'created_at']

    def get_available_balance(self, obj):
        from .models import get_balance, get_held_balance
        return get_balance(obj.id) - get_held_balance(obj.id)

    def get_held_balance(self, obj):
        from .models import get_held_balance
        return get_held_balance(obj.id)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount_paise', 'type', 'description', 'created_at']


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            'id', 'amount_paise', 'bank_account_id', 'status',
            'retry_count', 'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = ['status', 'retry_count', 'processed_at']


class PayoutRequestSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=255)
