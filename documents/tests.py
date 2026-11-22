"""Comprehensive tests for documents app."""

import json
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from io import BytesIO
from documents.models import Document

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
def other_user():
    return User.objects.create_user(email='other@test.com', password='TestPass123!')


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
        title='Test Document',
        content={'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Hello'}]}]},
        owner=owner,
    )


@pytest.mark.django_db
class TestDocumentCreation:
    def test_create_document(self, owner_client):
        response = owner_client.post('/api/documents/', {
            'title': 'My Doc',
            'content': json.dumps({'type': 'doc', 'content': []}),
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'My Doc'
        assert 'id' in response.data

    def test_create_document_default_title(self, owner_client):
        response = owner_client.post('/api/documents/', {}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Untitled Document'

    def test_create_document_unauthenticated(self, api_client):
        response = api_client.post('/api/documents/', {'title': 'Doc'}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentRetrieval:
    def test_list_own_documents(self, owner_client, sample_doc):
        response = owner_client.get('/api/documents/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['title'] == 'Test Document'

    def test_get_document_detail(self, owner_client, sample_doc):
        response = owner_client.get(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Test Document'
        assert response.data['content']['type'] == 'doc'

    def test_cannot_access_others_document(self, collab_client, sample_doc):
        response = collab_client.get(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_documents(self, owner_client, sample_doc):
        response = owner_client.get('/api/documents/?search=Test')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_filter_owned_documents(self, owner_client, sample_doc):
        response = owner_client.get('/api/documents/?filter=owned')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1


@pytest.mark.django_db
class TestDocumentUpdate:
    def test_update_document_title(self, owner_client, sample_doc):
        response = owner_client.patch(
            f'/api/documents/{sample_doc.id}/',
            {'title': 'Updated Title'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'

    def test_update_document_content(self, owner_client, sample_doc):
        new_content = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Updated'}]}]}
        response = owner_client.patch(
            f'/api/documents/{sample_doc.id}/',
            {'content': new_content},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['content'] == new_content

    def test_cannot_update_others_document(self, collab_client, sample_doc):
        response = collab_client.patch(
            f'/api/documents/{sample_doc.id}/',
            {'title': 'Hacked'},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestDocumentDeletion:
    def test_delete_document(self, owner_client, sample_doc):
        response = owner_client.delete(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Document.objects.filter(id=sample_doc.id).exists()

    def test_cannot_delete_others_document(self, collab_client, sample_doc):
        response = collab_client.delete(f'/api/documents/{sample_doc.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Document.objects.filter(id=sample_doc.id).exists()


@pytest.mark.django_db
class TestDocumentImport:
    def test_import_txt_file(self, owner_client):
        content = b'Hello World\n\nThis is a test.'
        file = BytesIO(content)
        file.name = 'test.txt'
        response = owner_client.post('/api/documents/import/', {'file': file}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'test'
        assert response.data['content']['type'] == 'doc'

    def test_import_md_file(self, owner_client):
        content = b'# Heading\n\nSome **bold** text.\n\n- Item 1\n- Item 2\n'
        file = BytesIO(content)
        file.name = 'readme.md'
        response = owner_client.post('/api/documents/import/', {'file': file}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'readme'

    def test_reject_unsupported_format(self, owner_client):
        file = BytesIO(b'data')
        file.name = 'test.pdf'
        response = owner_client.post('/api/documents/import/', {'file': file}, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reject_no_file(self, owner_client):
        response = owner_client.post('/api/documents/import/', {}, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
