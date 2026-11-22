"""Document models."""

import uuid
from django.conf import settings
from django.db import models


class Document(models.Model):
    """Rich-text document model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default='Untitled Document')
    content = models.JSONField(default=dict, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_documents',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
        ]

    def __str__(self):
        return f'{self.title} (by {self.owner.email})'
