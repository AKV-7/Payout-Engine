from django.urls import path
from .views import (
    MerchantDetailView,
    TransactionListView,
    PayoutListCreateView,
    PayoutDetailView,
)

urlpatterns = [
    path('merchants/me/', MerchantDetailView.as_view(), name='merchant-me'),
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('payouts/', PayoutListCreateView.as_view(), name='payout-list-create'),
    path('payouts/<uuid:pk>/', PayoutDetailView.as_view(), name='payout-detail'),
]
