from django.db import models
from model_utils.fields import AutoCreatedField, AutoLastModifiedField

# Create your models here.

class BaseModel(models.Model):
    created = AutoCreatedField('Created')
    last_modified = AutoLastModifiedField('Last modified')
    deleted = models.BooleanField('Is deleted', default=False)
    disabled = models.BooleanField('Is disabled', default=False)

    class Meta:
        abstract = True