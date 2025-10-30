from .base import *

print('ruining production settings')

DEBUG = False

ALLOWED_HOSTS = ['*']
print('ruining production settings')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
