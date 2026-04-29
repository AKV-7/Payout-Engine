import os
from pathlib import Path
import environ

env = environ.Env(
    DEBUG=(bool, False),
    DATABASE_URL=(str, 'postgres://postgres:postgres@db:5432/playto'),
    REDIS_URL=(str, 'redis://redis:6379/0'),
    SECRET_KEY=(str, 'change-me-in-production'),
    ALLOWED_HOSTS=(list, ['*']),
)

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = ['*'] # env('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'ledger.apps.LedgerConfig',
    'django_celery_beat',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'playto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'playto.wsgi.application'

DATABASES = {
    'default': env.db(),
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'idempotency-key',
    'x-merchant-id',
    'X-Merchant-ID',
]

CELERY_BROKER_URL = env('REDIS_URL')
CELERY_RESULT_BACKEND = env('REDIS_URL')

if CELERY_BROKER_URL.startswith('rediss://'):
    CELERY_BROKER_USE_SSL = {'ssl_cert_reqs': 'none'}
    CELERY_REDIS_BACKEND_USE_SSL = {'ssl_cert_reqs': 'none'}

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Periodic tasks
from datetime import timedelta
CELERY_BEAT_SCHEDULE = {
    'retry-stuck-payouts': {
        'task': 'ledger.tasks.retry_stuck_processing',
        'schedule': timedelta(seconds=15),
    },
    'cleanup-idempotency-keys': {
        'task': 'ledger.tasks.cleanup_idempotency_keys',
        'schedule': timedelta(hours=24),
    },
}

# --- Force-seed merchants on startup (Python runtime) ---
import sys as _sys
if 'gunicorn' in ' '.join(_sys.argv) or 'runserver' in ' '.join(_sys.argv):
    try:
        import django as _django
        _django.setup()
        from ledger.models import Merchant, Transaction as _T
        import uuid as _uuid

        _fixed = [
            'f47ac10b-58cc-4372-a567-0e02b2c3d479',
            'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            '5a6b7c8d-9e0f-1234-5678-9abcdef01234',
        ]

        _existing = Merchant.objects.filter(
            id__in=[_uuid.UUID(u) for u in _fixed]
        ).count()

        if _existing < 3:
            print("[Startup Seed] Force seeding merchants with correct UUIDs...")
            # Delete in correct order: transactions first
            _T.objects.all().delete()
            Merchant.objects.all().delete()

            _data = [
                ('Rahul Designs', 'rahul@designs.in', _fixed[0], [
                    (2500000, 'Payment from US client #1'),
                    (1500000, 'Payment from UK client #2'),
                    (1000000, 'Payment from EU client #3'),
                ]),
                ('Priya Tech Solutions', 'priya@tech.in', _fixed[1], [
                    (2500000, 'SaaS subscription payment'),
                ]),
                ('Amit Studio', 'amit@studio.in', _fixed[2], [
                    (5000000, 'Video production advance'),
                    (2500000, 'Final delivery payment'),
                ]),
            ]

            for _name, _email, _uid, _credits in _data:
                _m = Merchant.objects.create(
                    id=_uuid.UUID(_uid), name=_name, email=_email
                )
                print(f"[Startup Seed] Created: {_name}")
                for _amount, _desc in _credits:
                    _T.objects.create(
                        merchant=_m, amount_paise=_amount,
                        type=_T.CREDIT, description=_desc
                    )

            print("[Startup Seed] Done!")
    except Exception as _e:
        print(f"[Startup Seed] Error: {_e}")
