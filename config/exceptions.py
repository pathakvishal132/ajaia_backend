"""Centralized exception handling for REST framework."""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """Custom exception handler that returns consistent error responses."""
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'error': True,
            'status_code': response.status_code,
        }
        if isinstance(response.data, dict):
            error_data['details'] = response.data
        elif isinstance(response.data, list):
            error_data['details'] = {'errors': response.data}
        else:
            error_data['details'] = {'message': str(response.data)}
        response.data = error_data
        return response

    # Handle unexpected exceptions
    return Response(
        {
            'error': True,
            'status_code': 500,
            'details': {'message': 'An unexpected error occurred.'},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
