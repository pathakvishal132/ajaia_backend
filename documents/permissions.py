"""Document permissions."""

from rest_framework import permissions
from sharing.models import DocumentShare


class IsDocumentOwner(permissions.BasePermission):
    """Allow access only to the document owner."""

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsDocumentAccessible(permissions.BasePermission):
    """Allow access to owner or users with shares."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        # Owner has full access
        if obj.owner == user:
            return True
        # Check shares
        share = DocumentShare.objects.filter(
            document=obj, shared_with=user
        ).first()
        if not share:
            return False
        # Viewers can only read
        if request.method in permissions.SAFE_METHODS:
            return True
        # Editors can modify
        return share.permission == DocumentShare.Permission.EDITOR
