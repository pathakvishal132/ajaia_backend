"""Comprehensive tests for accounts app."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user():
    def _create_user(email='test@example.com', password='TestPass123!', **kwargs):
        return User.objects.create_user(email=email, password=password, **kwargs)
    return _create_user


@pytest.fixture
def authenticated_client(api_client, create_user):
    user = create_user()
    response = api_client.post('/api/auth/login/', {
        'email': 'test@example.com',
        'password': 'TestPass123!',
    })
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["tokens"]["access"]}')
    return api_client, user


@pytest.mark.django_db
class TestRegistration:
    def test_register_success(self, api_client):
        response = api_client.post('/api/auth/register/', {
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'first_name': 'New',
            'last_name': 'User',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert response.data['user']['email'] == 'newuser@example.com'

    def test_register_password_mismatch(self, api_client):
        response = api_client.post('/api/auth/register/', {
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'WrongPass123!',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, create_user):
        create_user(email='dup@example.com')
        response = api_client.post('/api/auth/register/', {
            'email': 'dup@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_fields(self, api_client):
        response = api_client.post('/api/auth/register/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client, create_user):
        create_user(email='login@example.com', password='TestPass123!')
        response = api_client.post('/api/auth/login/', {
            'email': 'login@example.com',
            'password': 'TestPass123!',
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert response.data['user']['email'] == 'login@example.com'

    def test_login_wrong_password(self, api_client, create_user):
        create_user(email='login@example.com', password='TestPass123!')
        response = api_client.post('/api/auth/login/', {
            'email': 'login@example.com',
            'password': 'WrongPassword!',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post('/api/auth/login/', {
            'email': 'nobody@example.com',
            'password': 'TestPass123!',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProfile:
    def test_get_profile(self, authenticated_client):
        client, user = authenticated_client
        response = client.get('/api/auth/profile/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_profile_unauthenticated(self, api_client):
        response = api_client.get('/api/auth/profile/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSeedDemoData:
    """The demo seed is what reviewers log in with, so it must be correct and idempotent."""

    def test_seed_creates_accounts_and_shared_sample(self, api_client):
        from django.core.management import call_command
        from documents.models import Document
        from sharing.models import DocumentShare

        call_command('seed_users')
        call_command('seed_users')  # second run must not duplicate anything

        assert User.objects.filter(email__in=['owner@example.com', 'collaborator@example.com']).count() == 2
        assert Document.objects.count() == 1
        share = DocumentShare.objects.get()
        assert share.shared_with.email == 'collaborator@example.com'
        assert share.permission == 'editor'

        # Collaborator can log in with the documented password and sees the doc as shared.
        login = api_client.post('/api/auth/login/', {
            'email': 'collaborator@example.com', 'password': 'Test@12345',
        })
        assert login.status_code == status.HTTP_200_OK
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["tokens"]["access"]}')
        shared = api_client.get('/api/documents/?filter=shared')
        assert [d['permission'] for d in shared.data['results']] == ['editor']
        assert api_client.get('/api/documents/?filter=owned').data['results'] == []


def test_health_endpoint_is_public(client):
    response = client.get('/api/health/')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
