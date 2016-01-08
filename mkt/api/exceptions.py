from django.conf import settings
from django.core.signals import got_request_exception

from rest_framework import status
from rest_framework.exceptions import APIException, ParseError as DRFParseError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class AlreadyPurchased(Exception):
    pass


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Conflict detected.'

    def __init__(self, detail=None):
        self.detail = detail or self.default_detail


class NotImplemented(APIException):
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    default_detail = 'API not implemented.'

    def __init__(self, detail=None):
        self.detail = detail or self.default_detail


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service unavailable at this time.'

    def __init__(self, detail=None):
        self.detail = detail or self.default_detail


def custom_exception_handler(exc, context=None):
    """
    Custom exception handler for DRF, which doesn't provide one for HTTP
    responses like tastypie does.
    """
    # If propagate is true, bail early.
    if settings.DEBUG_PROPAGATE_EXCEPTIONS:
        raise

    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If the response is None, then DRF didn't handle the exception and we
    # should do it ourselves.
    if response is None:
        # Start with a generic default error message.
        data = {"detail": "Internal Server Error"}

        # Include traceback if API_SHOW_TRACEBACKS is active.
        if getattr(settings, 'API_SHOW_TRACEBACKS', settings.DEBUG):
            import traceback
            import sys

            data['error_message'] = unicode(exc)
            data['traceback'] = '\n'.join(
                traceback.format_exception(*(sys.exc_info())))

        request = getattr(exc, '_request', None)
        klass = getattr(exc, '_klass', None)

        # Send the signal so other apps are aware of the exception.
        got_request_exception.send(klass, request=request)

        # Send the 500 response back.
        response = Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response


class HttpLegallyUnavailable(APIException):
    status_code = 451
    default_detail = 'Legally unavailable.'

    def __init__(self, detail=None):
        self.detail = {'detail': detail or self.default_detail}


class ParseError(DRFParseError):
    def __init__(self, detail):
        self.detail = {u'detail': detail or self.default_detail}
