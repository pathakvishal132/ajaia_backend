"""Sharing views."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document
from .models import DocumentShare
from .serializers import DocumentShareSerializer, ShareCreateSerializer, ShareUpdateSerializer

User = get_user_model()


class ShareDocumentView(APIView):
    """Share a document with another user."""

    def post(self, request, document_id):
        document = get_object_or_404(Document, pk=document_id)

        # Only owner can share
        if document.owner != request.user:
            return Response(
                {'error': True, 'details': {'message': 'Only the document owner can share this document.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ShareCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        permission = serializer.validated_data['permission']
        target_user = User.objects.get(email=email)

        # Cannot share with yourself
        if target_user == request.user:
            return Response(
                {'error': True, 'details': {'message': 'You cannot share a document with yourself.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for existing share
        share, created = DocumentShare.objects.update_or_create(
            document=document,
            shared_with=target_user,
            defaults={'permission': permission},
        )

        return Response(
            DocumentShareSerializer(share).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DocumentSharesListView(generics.ListAPIView):
    """List all shares for a document."""

    serializer_class = DocumentShareSerializer

    def get_queryset(self):
        document = get_object_or_404(Document, pk=self.kwargs['document_id'])
        # Only owner can see all shares
        if document.owner != self.request.user:
            return DocumentShare.objects.none()
        return DocumentShare.objects.filter(document=document)


class DocumentShareDetailView(APIView):
    """Update or revoke a document share."""

    def patch(self, request, document_id, share_id):
        document = get_object_or_404(Document, pk=document_id)
        if document.owner != request.user:
            return Response(
                {'error': True, 'details': {'message': 'Only the owner can modify shares.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        share = get_object_or_404(DocumentShare, pk=share_id, document=document)
        serializer = ShareUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        share.permission = serializer.validated_data['permission']
        share.save()
        return Response(DocumentShareSerializer(share).data)

    def delete(self, request, document_id, share_id):
        document = get_object_or_404(Document, pk=document_id)
        if document.owner != request.user:
            return Response(
                {'error': True, 'details': {'message': 'Only the owner can revoke shares.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        share = get_object_or_404(DocumentShare, pk=share_id, document=document)
        share.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
