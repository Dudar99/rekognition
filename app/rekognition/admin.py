from django.contrib import admin

# Register your models here.
from .models import Person, Collection

admin.site.register(Person)
admin.site.register(Collection)