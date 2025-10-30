from .base import *
import os


print('ruining local settings')


DEBUG = True

ALLOWED_HOSTS = ['*']

# media url
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'