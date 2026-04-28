from django.contrib import admin
from .models import Merchant, Transaction, Payout, IdempotencyRecord


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at']
    search_fields = ['name', 'email']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'type', 'amount_paise', 'description', 'created_at']
    list_filter = ['type', 'created_at']


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['id', 'merchant', 'amount_paise', 'status', 'bank_account_id', 'created_at']
    list_filter = ['status', 'created_at']


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'key', 'created_at']
