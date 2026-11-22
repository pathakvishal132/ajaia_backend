"""Document sharing models."""

from django.conf import settings
from django.db import models


class DocumentShare(models.Model):
    """Represents sharing a document with another user."""

    class Permission(models.TextChoices):
        VIEWER = 'viewer', 'Viewer'
        EDITOR = 'editor', 'Editor'

    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='shares',
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_documents',
    )
    permission = models.CharField(
        max_length=10,
        choices=Permission.choices,
        default=Permission.VIEWER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_shares'
        unique_together = ('document', 'shared_with')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.document.title} -> {self.shared_with.email} ({self.permission})'
