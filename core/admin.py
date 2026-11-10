from django.contrib import admin
from .models import DocumentSequenceCounter, Customer, Supplier

admin.site.register(DocumentSequenceCounter)
admin.site.register(Customer)
admin.site.register(Supplier)
