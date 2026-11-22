"""Seed demo accounts and one shared sample document (idempotent)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from documents.models import Document
from sharing.models import DocumentShare

User = get_user_model()

DEMO_PASSWORD = 'Test@12345'
SAMPLE_TITLE = 'Welcome to DocEditor'


def _text(text, *marks):
    node = {'type': 'text', 'text': text}
    if marks:
        node['marks'] = [{'type': m} for m in marks]
    return node


def _para(*children):
    return {'type': 'paragraph', 'content': list(children)}


def _list(kind, *items):
    return {
        'type': kind,
        'content': [{'type': 'listItem', 'content': [_para(_text(i))]} for i in items],
    }


SAMPLE_CONTENT = {
    'type': 'doc',
    'content': [
        {'type': 'heading', 'attrs': {'level': 1}, 'content': [_text('Welcome to DocEditor')]},
        _para(
            _text('This document is owned by '), _text('owner@example.com', 'bold'),
            _text(' and shared with '), _text('collaborator@example.com', 'italic'),
            _text(' as an '), _text('editor', 'underline'), _text('.'),
        ),
        {'type': 'heading', 'attrs': {'level': 2}, 'content': [_text('Try it out')]},
        _list(
            'bulletList',
            'Format text with the toolbar or Cmd/Ctrl+B, I, U',
            'Changes autosave about two seconds after you stop typing',
            'Use Share (owner only) to grant viewer or editor access',
        ),
        {'type': 'heading', 'attrs': {'level': 2}, 'content': [_text('Import a file')]},
        _list(
            'orderedList',
            'Go back to the dashboard',
            'Click "Import File" and pick a .txt, .md or .docx file',
            'It opens as a new editable document you own',
        ),
    ],
}


class Command(BaseCommand):
    help = 'Seed demo user accounts and a shared sample document'

    def handle(self, *args, **options):
        users = [
            {'email': 'owner@example.com', 'first_name': 'Owner', 'last_name': 'User'},
            {'email': 'collaborator@example.com', 'first_name': 'Collaborator', 'last_name': 'User'},
        ]

        created_users = {}
        for data in users:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={'first_name': data['first_name'], 'last_name': data['last_name']},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.email}'))
            else:
                self.stdout.write(self.style.WARNING(f'User already exists: {user.email}'))
            created_users[data['email']] = user

        owner = created_users['owner@example.com']
        collaborator = created_users['collaborator@example.com']
        doc, created = Document.objects.get_or_create(
            owner=owner, title=SAMPLE_TITLE, defaults={'content': SAMPLE_CONTENT},
        )
        DocumentShare.objects.get_or_create(
            document=doc, shared_with=collaborator,
            defaults={'permission': DocumentShare.Permission.EDITOR},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created sample document: {doc.title}'))
