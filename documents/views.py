"""Document views."""

import os
import markdown
from django.conf import settings
from django.db.models import Q
from rest_framework import generics, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.views import APIView

from sharing.models import DocumentShare
from .models import Document
from .permissions import IsDocumentAccessible, IsDocumentOwner
from .serializers import (
    DocumentCreateSerializer,
    DocumentDetailSerializer,
    DocumentListSerializer,
)


class DocumentListCreateView(generics.ListCreateAPIView):
    """List user's documents or create a new one."""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DocumentCreateSerializer
        return DocumentListSerializer

    def get_queryset(self):
        user = self.request.user
        filter_type = self.request.query_params.get('filter', 'all')
        search = self.request.query_params.get('search', '').strip()

        if filter_type == 'owned':
            qs = Document.objects.filter(owner=user)
        elif filter_type == 'shared':
            shared_doc_ids = DocumentShare.objects.filter(
                shared_with=user
            ).values_list('document_id', flat=True)
            qs = Document.objects.filter(id__in=shared_doc_ids)
        else:
            shared_doc_ids = DocumentShare.objects.filter(
                shared_with=user
            ).values_list('document_id', flat=True)
            qs = Document.objects.filter(
                Q(owner=user) | Q(id__in=shared_doc_ids)
            )

        if search:
            qs = qs.filter(title__icontains=search)

        return qs.distinct()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()
        return Response(
            DocumentDetailSerializer(doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a document."""

    serializer_class = DocumentDetailSerializer
    permission_classes = (permissions.IsAuthenticated, IsDocumentAccessible)
    lookup_field = 'pk'

    def get_queryset(self):
        user = self.request.user
        shared_doc_ids = DocumentShare.objects.filter(
            shared_with=user
        ).values_list('document_id', flat=True)
        return Document.objects.filter(
            Q(owner=user) | Q(id__in=shared_doc_ids)
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.owner != request.user:
            return Response(
                {'error': True, 'details': {'message': 'Only the owner can delete this document.'}},
                status=status.HTTP_403_FORBIDDEN,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentImportView(APIView):
    """Import a document from an uploaded file."""

    parser_classes = (parsers.MultiPartParser, parsers.FormParser)

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': True, 'details': {'message': 'No file provided.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
        if uploaded_file.size > max_size:
            return Response(
                {'error': True, 'details': {'message': f'File exceeds maximum size of {max_size // (1024 * 1024)}MB.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file extension
        _, ext = os.path.splitext(uploaded_file.name)
        ext = ext.lower()
        allowed = getattr(settings, 'ALLOWED_UPLOAD_EXTENSIONS', ['.txt', '.md', '.docx'])
        if ext not in allowed:
            return Response(
                {'error': True, 'details': {'message': f'Unsupported file format. Allowed: {", ".join(allowed)}'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content = self._parse_file(uploaded_file, ext)
        except Exception as e:
            return Response(
                {'error': True, 'details': {'message': f'Error parsing file: {str(e)}'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = os.path.splitext(uploaded_file.name)[0]
        doc = Document.objects.create(
            title=title,
            content=content,
            owner=request.user,
        )
        return Response(
            DocumentDetailSerializer(doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def _parse_file(self, uploaded_file, ext):
        """Parse file content into TipTap-compatible JSON."""
        if ext == '.txt':
            return self._parse_text(uploaded_file.read().decode('utf-8', errors='replace'))
        elif ext == '.md':
            return self._parse_markdown(uploaded_file.read().decode('utf-8', errors='replace'))
        elif ext == '.docx':
            return self._parse_docx(uploaded_file)
        raise ValueError(f'Unsupported format: {ext}')

    def _parse_text(self, text):
        """Convert plain text to TipTap JSON."""
        paragraphs = text.split('\n\n') if '\n\n' in text else text.split('\n')
        content = []
        for para in paragraphs:
            para = para.strip()
            if para:
                content.append({
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': para}],
                })
        return {'type': 'doc', 'content': content} if content else {'type': 'doc', 'content': [{'type': 'paragraph'}]}

    def _parse_markdown(self, md_text):
        """Convert markdown to TipTap JSON."""
        content = []
        lines = md_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # Headings
            if stripped.startswith('### '):
                content.append({
                    'type': 'heading',
                    'attrs': {'level': 3},
                    'content': [{'type': 'text', 'text': stripped[4:]}],
                })
            elif stripped.startswith('## '):
                content.append({
                    'type': 'heading',
                    'attrs': {'level': 2},
                    'content': [{'type': 'text', 'text': stripped[3:]}],
                })
            elif stripped.startswith('# '):
                content.append({
                    'type': 'heading',
                    'attrs': {'level': 1},
                    'content': [{'type': 'text', 'text': stripped[2:]}],
                })
            # Bullet lists
            elif stripped.startswith('- ') or stripped.startswith('* '):
                items = []
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    item_text = lines[i].strip()[2:]
                    items.append({
                        'type': 'listItem',
                        'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': item_text}]}],
                    })
                    i += 1
                content.append({'type': 'bulletList', 'content': items})
                continue
            # Numbered lists
            elif stripped and stripped[0].isdigit() and '. ' in stripped:
                items = []
                while i < len(lines) and lines[i].strip() and lines[i].strip()[0].isdigit() and '. ' in lines[i].strip():
                    item_text = lines[i].strip().split('. ', 1)[1]
                    items.append({
                        'type': 'listItem',
                        'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': item_text}]}],
                    })
                    i += 1
                content.append({'type': 'orderedList', 'content': items})
                continue
            else:
                # Parse inline formatting
                text_content = self._parse_inline_markdown(stripped)
                content.append({
                    'type': 'paragraph',
                    'content': text_content,
                })

            i += 1

        return {'type': 'doc', 'content': content} if content else {'type': 'doc', 'content': [{'type': 'paragraph'}]}

    def _parse_inline_markdown(self, text):
        """Parse bold and italic from markdown text into TipTap marks."""
        import re
        result = []
        # Simple approach: handle **bold** and *italic*
        pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*|__(.+?)__|_(.+?)_|([^*_]+))')
        for match in pattern.finditer(text):
            if match.group(2):  # **bold**
                result.append({'type': 'text', 'text': match.group(2), 'marks': [{'type': 'bold'}]})
            elif match.group(3):  # *italic*
                result.append({'type': 'text', 'text': match.group(3), 'marks': [{'type': 'italic'}]})
            elif match.group(4):  # __bold__
                result.append({'type': 'text', 'text': match.group(4), 'marks': [{'type': 'bold'}]})
            elif match.group(5):  # _italic_
                result.append({'type': 'text', 'text': match.group(5), 'marks': [{'type': 'italic'}]})
            elif match.group(6):  # plain text
                result.append({'type': 'text', 'text': match.group(6)})
        return result if result else [{'type': 'text', 'text': text}]

    def _parse_docx(self, uploaded_file):
        """Convert .docx to TipTap JSON."""
        from docx import Document as DocxDocument
        from io import BytesIO

        doc = DocxDocument(BytesIO(uploaded_file.read()))
        content = []

        for para in doc.paragraphs:
            if not para.text.strip():
                continue

            # Determine paragraph type
            style_name = (para.style.name or '').lower()
            if 'heading 1' in style_name:
                node = {'type': 'heading', 'attrs': {'level': 1}}
            elif 'heading 2' in style_name:
                node = {'type': 'heading', 'attrs': {'level': 2}}
            elif 'heading 3' in style_name:
                node = {'type': 'heading', 'attrs': {'level': 3}}
            else:
                node = {'type': 'paragraph'}

            # Parse runs for formatting
            text_content = []
            for run in para.runs:
                if not run.text:
                    continue
                text_node = {'type': 'text', 'text': run.text}
                marks = []
                if run.bold:
                    marks.append({'type': 'bold'})
                if run.italic:
                    marks.append({'type': 'italic'})
                if run.underline:
                    marks.append({'type': 'underline'})
                if marks:
                    text_node['marks'] = marks
                text_content.append(text_node)

            if text_content:
                node['content'] = text_content
            else:
                node['content'] = [{'type': 'text', 'text': para.text}]

            content.append(node)

        return {'type': 'doc', 'content': content} if content else {'type': 'doc', 'content': [{'type': 'paragraph'}]}
