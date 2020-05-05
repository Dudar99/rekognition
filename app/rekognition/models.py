from django.db import models


# Create your models here.

class Collection(models.Model):
    collection_id = models.CharField(max_length=100)


class Person(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    face_id = models.CharField(max_length=100)
    image_path = models.CharField(max_length=100)
    collection_id = models.ManyToManyField(Collection)