import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playto.settings')

app = Celery('playto')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'cleanup-idempotency-keys': {
        'task': 'ledger.tasks.cleanup_idempotency_keys',
        'schedule': crontab(minute=0),  # every hour
    },
    'retry-stuck-payouts': {
        'task': 'ledger.tasks.retry_stuck_processing',
        'schedule': 30.0,  # every 30 seconds
    },
}
