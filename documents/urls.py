"""Document URL configuration."""

from django.urls import path
from . import views
from sharing import views as sharing_views

urlpatterns = [
    path('', views.DocumentListCreateView.as_view(), name='document-list'),
    path('<uuid:pk>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('import/', views.DocumentImportView.as_view(), name='document-import'),
    # Sharing endpoints
    path('<uuid:document_id>/share/', sharing_views.ShareDocumentView.as_view(), name='document-share'),
    path('<uuid:document_id>/shares/', sharing_views.DocumentSharesListView.as_view(), name='document-shares-list'),
    path(
        '<uuid:document_id>/shares/<int:share_id>/',
        sharing_views.DocumentShareDetailView.as_view(),
        name='document-share-detail',
    ),
]
