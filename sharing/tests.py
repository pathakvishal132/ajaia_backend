"""Comprehensive tests for sharing app."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from documents.models import Document
from sharing.models import DocumentShare

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner():
    return User.objects.create_user(email='owner@test.com', password='TestPass123!')


@pytest.fixture
def collaborator():
    return User.objects.create_user(email='collab@test.com', password='TestPass123!')


@pytest.fixture
def owner_client(api_client, owner):
    response = api_client.post('/api/auth/login/', {
        'email': 'owner@test.com', 'password': 'TestPass123!'
    })
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["tokens"]["access"]}')
    return api_client


@pytest.fixture
def collab_client(collaborator):
    client = APIClient()
    response = client.post('/api/auth/login/', {
        'email': 'collab@test.com', 'password': 'TestPass123!'
    })
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["tokens"]["access"]}')
    return client


@pytest.fixture
def sample_doc(owner):
    return Document.objects.create(
        title='Shared Doc',
        content={'type': 'doc', 'content': []},
        owner=owner,
    )


@pytest.mark.django_db
class TestShareDocument:
    def test_share_as_viewer(self, owner_client, sample_doc, collaborator):
        response = owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'viewer'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['permission'] == 'viewer'

    def test_share_as_editor(self, owner_client, sample_doc, collaborator):
        response = owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'editor'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['permission'] == 'editor'

    def test_cannot_share_with_self(self, owner_client, sample_doc):
        response = owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'owner@test.com', 'permission': 'viewer'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_owner_cannot_share(self, collab_client, sample_doc, collaborator):
        response = collab_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'someone@test.com', 'permission': 'viewer'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_share_nonexistent_email(self, owner_client, sample_doc):
        response = owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'nobody@test.com', 'permission': 'viewer'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestViewerPermission:
    def test_viewer_can_read(self, owner_client, collab_client, sample_doc, collaborator):
        # Share as viewer
        owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'viewer'},
            format='json',
        )
        # Viewer can read
        response = collab_client.get(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_cannot_edit(self, owner_client, collab_client, sample_doc, collaborator):
        # Share as viewer
        owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'viewer'},
            format='json',
        )
        # Viewer cannot modify
        response = collab_client.patch(
            f'/api/documents/{sample_doc.id}/',
            {'title': 'Modified by Viewer'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestEditorPermission:
    def test_editor_can_read(self, owner_client, collab_client, sample_doc, collaborator):
        owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'editor'},
            format='json',
        )
        response = collab_client.get(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_editor_can_edit(self, owner_client, collab_client, sample_doc, collaborator):
        owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'editor'},
            format='json',
        )
        response = collab_client.patch(
            f'/api/documents/{sample_doc.id}/',
            {'title': 'Modified by Editor'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Modified by Editor'

    def test_editor_cannot_delete(self, owner_client, collab_client, sample_doc, collaborator):
        owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'editor'},
            format='json',
        )
        response = collab_client.delete(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRevokeAccess:
    def test_revoke_share(self, owner_client, collab_client, sample_doc, collaborator):
        # Share
        share_response = owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'editor'},
            format='json',
        )
        share_id = share_response.data['id']

        # Collaborator can access
        response = collab_client.get(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_200_OK

        # Revoke
        response = owner_client.delete(f'/api/documents/{sample_doc.id}/shares/{share_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Collaborator can no longer access
        response = collab_client.get(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_shares(self, owner_client, sample_doc, collaborator):
        owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'viewer'},
            format='json',
        )
        response = owner_client.get(f'/api/documents/{sample_doc.id}/shares/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_update_share_permission(self, owner_client, sample_doc, collaborator):
        share_response = owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'viewer'},
            format='json',
        )
        share_id = share_response.data['id']

        response = owner_client.patch(
            f'/api/documents/{sample_doc.id}/shares/{share_id}/',
            {'permission': 'editor'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['permission'] == 'editor'


@pytest.mark.django_db
class TestSharedDocumentListing:
    def test_shared_docs_appear_in_list(self, owner_client, collab_client, sample_doc, collaborator):
        owner_client.post(
            f'/api/documents/{sample_doc.id}/share/',
            {'email': 'collab@test.com', 'permission': 'viewer'},
            format='json',
        )
        response = collab_client.get('/api/documents/?filter=shared')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['title'] == 'Shared Doc'
