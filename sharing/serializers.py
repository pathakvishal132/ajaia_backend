"""Sharing serializers."""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import DocumentShare

User = get_user_model()


class ShareCreateSerializer(serializers.Serializer):
    """Serializer for creating a document share."""

    email = serializers.EmailField()
    permission = serializers.ChoiceField(choices=DocumentShare.Permission.choices, default='viewer')

    def validate_email(self, value):
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('No user found with this email address.')
        return value


class DocumentShareSerializer(serializers.ModelSerializer):
    """Serializer for document share listing."""

    shared_with_email = serializers.CharField(source='shared_with.email', read_only=True)
    shared_with_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentShare
        fields = ('id', 'shared_with', 'shared_with_email', 'shared_with_name', 'permission', 'created_at')
        read_only_fields = ('id', 'shared_with', 'shared_with_email', 'shared_with_name', 'created_at')

    def get_shared_with_name(self, obj):
        user = obj.shared_with
        name = f'{user.first_name} {user.last_name}'.strip()
        return name or user.email


class ShareUpdateSerializer(serializers.Serializer):
    """Serializer for updating share permission."""

    permission = serializers.ChoiceField(choices=DocumentShare.Permission.choices)
