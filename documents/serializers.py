"""Document serializers."""

from rest_framework import serializers
from .models import Document
from accounts.serializers import UserSerializer


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer for document listing."""

    owner = UserSerializer(read_only=True)
    permission = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ('id', 'title', 'owner', 'created_at', 'updated_at', 'permission')
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')

    def get_permission(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        if obj.owner == request.user:
            return 'owner'
        share = obj.shares.filter(shared_with=request.user).first()
        if share:
            return share.permission
        return None


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer for document detail/create/update."""

    owner = UserSerializer(read_only=True)
    permission = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ('id', 'title', 'content', 'owner', 'created_at', 'updated_at', 'permission')
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')

    def get_permission(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        if obj.owner == request.user:
            return 'owner'
        share = obj.shares.filter(shared_with=request.user).first()
        if share:
            return share.permission
        return None


class DocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating documents."""

    class Meta:
        model = Document
        fields = ('id', 'title', 'content')
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)
