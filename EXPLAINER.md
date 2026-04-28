# EXPLAINER.md

## 1. The Ledger

### Balance Calculation Query

```python
def get_balance(merchant_id):
    result = Transaction.objects.filter(merchant_id=merchant_id).aggregate(
        credits=Sum('amount_paise', filter=Q(type=Transaction.CREDIT)),
        debits=Sum('amount_paise', filter=Q(type=Transaction.DEBIT)),
    )
    credits = result['credits'] or 0
    debits = result['debits'] or 0
    return credits - debits
```

### Why Credits and Debits?

I modeled the ledger as immutable credit/debit entries rather than a mutable `balance` column for three reasons:

1. **Single source of truth**: Balance is derived, not stored. There is no `balance` field on the `Merchant` model that could drift out of sync with the transaction history.
2. **Audit trail**: Every rupee movement is permanently recorded. A failed payout creates no new transaction (the hold was conceptual via the `Payout` record), but a completed payout creates a `debit` transaction. If we had created a debit at request time, a failure would require a compensating `credit` — and both would be visible in the ledger.
3. **Database-level correctness**: The aggregation happens in a single SQL query. No Python iteration, no memory bloat, no stale reads between two separate queries.

The held balance is computed separately as the sum of `Payout` records in `pending` or `processing` state. Available balance = `get_balance() - get_held_balance()`.

---

## 2. The Lock

### Exact Code

```python
@transaction.atomic
def create(self, request, *args, **kwargs):
    # ... validation ...

    with transaction.atomic():
        # Lock merchant row
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)

        # Single-query balance inside the locked transaction
        total_balance = get_balance(merchant.id)
        held_balance = get_held_balance(merchant.id)
        available_balance = total_balance - held_balance

        if available_balance < amount_paise:
            raise InsufficientFunds(...)

        payout = Payout.objects.create(...)
        IdempotencyRecord.objects.create(...)
```

### Database Primitive

This relies on **PostgreSQL row-level pessimistic locking** via `SELECT FOR UPDATE`. When two concurrent requests hit the same merchant:

- Request A acquires the lock first, reads balance (10000), creates payout (6000), commits.
- Request B blocks on `select_for_update()` until A commits.
- Request B then reads the updated state: balance is still 10000, but held balance is now 6000, so available is 4000.
- Request B rejects with `InsufficientFunds`.

Without `select_for_update`, both requests could read 10000 simultaneously, both see available >= 6000, and both create payouts — resulting in a -2000 balance.

---

## 3. The Idempotency

### How the System Knows It Has Seen a Key Before

The `IdempotencyRecord` table has a **database-level unique constraint** on `(merchant, key)`:

```python
class Meta:
    unique_together = [['merchant', 'key']]
```

When a request arrives:
1. Fast path: Query `IdempotencyRecord` without locking. If found and payload hash matches, return stored response.
2. If not found: Enter `transaction.atomic()` with `select_for_update()` on merchant, create the payout, and attempt to insert the `IdempotencyRecord`.
3. If another request won the race and inserted first, we get `IntegrityError`, roll back, and return the winner's stored response.

### What If the First Request Is In-Flight?

- **Scenario**: Request 1 is inside `transaction.atomic()`, holding the `select_for_update()` lock, but has not yet created the `IdempotencyRecord`.
- **Request 2** arrives, tries `select_for_update()` on the same merchant row, and **blocks** until Request 1 commits.
- After Request 1 commits, Request 2 proceeds. It finds the `IdempotencyRecord` in the fast-path check and returns the stored response.

If Request 2 somehow sneaks past the fast path (extremely unlikely due to transaction isolation), it would attempt to insert the same `(merchant, key)` tuple and get `IntegrityError`, then fetch and return the stored response.

---

## 4. The State Machine

### Where Failed-to-Completed Is Blocked

```python
VALID_TRANSITIONS = {
    PENDING: [PROCESSING, FAILED],
    PROCESSING: [COMPLETED, FAILED],
    COMPLETED: [],      # Terminal
    FAILED: [],         # Terminal
}

def transition_to(self, new_status):
    if new_status not in VALID_TRANSITIONS[self.status]:
        raise InvalidStateTransition(
            f"Cannot transition from {self.status} to {new_status}"
        )
    self.status = new_status
    self.save(update_fields=['status', 'updated_at'])
```

A payout in `failed` state has `VALID_TRANSITIONS['failed'] = []`. Calling `transition_to('completed')` raises `InvalidStateTransition` because `'completed'` is not in the empty list.

This is enforced everywhere — in the Celery worker, in admin actions, and in any future API endpoints. The check is centralized in the model method, not duplicated across views.

---

## 5. The AI Audit

### Example 1: Balance Calculation with Python Arithmetic

**What AI gave me:**
```python
# AI suggested this in ChatGPT
balance = 0
for tx in Transaction.objects.filter(merchant=merchant):
    if tx.type == 'credit':
        balance += tx.amount_paise
    else:
        balance -= tx.amount_paise
```

**What I caught:**
- This loads **all** transactions into Python memory. For a merchant with years of history, this is O(N) memory and CPU.
- More critically, it happens **outside** the database transaction boundary when called before `select_for_update()`. Between the loop finishing and the lock being acquired, another request could commit a new transaction, making the balance stale.
- AI also suggested splitting into two separate `aggregate()` calls for credits and debits, which is better but still has a tiny race condition window between the two queries.

**What I replaced it with:**
```python
result = Transaction.objects.filter(merchant_id=merchant_id).aggregate(
    credits=Sum('amount_paise', filter=Q(type=Transaction.CREDIT)),
    debits=Sum('amount_paise', filter=Q(type=Transaction.DEBIT)),
)
```
- Single SQL query. Database handles the aggregation atomically.
- Called **inside** the `select_for_update()` transaction, so the result is consistent with the locked merchant state.

### Example 2: AI's "Optimistic" Idempotency Pattern

**What AI gave me:**
```python
# Common AI suggestion
if Payout.objects.filter(idempotency_key=key).exists():
    return Payout.objects.get(idempotency_key=key)
Payout.objects.create(...)
```

**What I caught:**
This is the classic **check-then-act** race condition. Between `exists()` and `create()`, another request can sneak in. Both threads see "does not exist", both create. This violates the "exactly one payout per key" invariant.

AI also missed that idempotency keys should be **scoped per merchant**, not global. Two different merchants should be able to use the same UUID without collision.

**What I replaced it with:**
- Database unique constraint on `(merchant, idempotency_key)` — the database is the single source of truth for uniqueness.
- `IntegrityError` handling: if the insert fails, roll back and return the existing stored response.
- Separate `IdempotencyRecord` table that stores the exact response body, so duplicate requests return byte-for-byte identical responses.

### Example 3: AI's Fund Return Pattern

**What AI gave me:**
```python
# AI suggested creating a "refund" transaction in a separate Celery task
@app.task
def refund_payout(payout_id):
    payout = Payout.objects.get(id=payout_id)
    payout.merchant.balance += payout.amount_paise  # Uses a balance field!
    payout.merchant.save()
```

**What I caught:**
- AI assumed a mutable `balance` field on `Merchant` (which I explicitly rejected).
- The refund happens in a **separate task** with no transaction linking it to the state transition. If the state transition commits but the refund task fails, the payout is marked failed but funds are not returned.
- No `select_for_update()` on the payout row, so the refund could race with another worker processing the same payout.

**What I replaced it with:**
- No separate refund task. Funds are never deducted at request time — they are only deducted when the payout reaches `completed`.
- A `failed` payout simply transitions state. No compensating transaction needed because no debit was ever created.
- If we had chosen to debit at request time (an alternative design), the refund would be an atomic `Transaction.objects.create(credit)` inside the same `transaction.atomic()` block as the state transition.

---

## Design Decisions

### Why No `balance` Field on Merchant?

A stored balance is a second source of truth. It can drift due to bugs, race conditions, or partial failures. The derived balance is always correct because it is a pure function of the immutable ledger.

### Why Debit on Completion, Not on Request?

If we debited at request time, a failed payout would require a compensating credit. This adds complexity and creates a window where the ledger shows a debit for a failed operation. By holding funds conceptually (via the `Payout` record) and only debiting on completion, the ledger always reflects reality.

### Why `BigIntegerField` in Paise?

Floats and Decimals have precision edge cases. Integers in the smallest currency unit (paise) are exact. `BigIntegerField` handles amounts up to ~9.2 quintillion paise (92 trillion rupees), which is more than sufficient.

### Why Not Event Sourcing?

Event sourcing is powerful but overkill for a minimal engine. The immutable transaction ledger provides 80% of the audit benefits with 20% of the complexity. If the system grows, migrating to event sourcing is straightforward because the ledger is already append-only.
