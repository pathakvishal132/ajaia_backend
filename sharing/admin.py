from django.contrib import admin
from .models import DocumentShare

@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = ('document', 'shared_with', 'permission', 'created_at')
    list_filter = ('permission',)
