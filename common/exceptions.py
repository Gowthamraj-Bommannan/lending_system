import logging

from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .constants import ErrorMessages, ErrorStatus, STATUS_MESSAGES
from .logging_utils import get_log_actor_key
from .api_log_messages import PROJECT_ERROR_LOG_MESSAGES, get_api_operation


logger = logging.getLogger(__name__)

PROJECT_DETAIL_LOG_MESSAGES = {
    ErrorMessages.VALIDATION_FAILED: 'Employee creation was rejected because required role information is missing or invalid.',
    ErrorMessages.REQUEST_FAILED: 'The API operation was rejected because the request could not be completed.',
    ErrorMessages.FIRST_NAME_REQUIRED: 'Employee creation was rejected because first name is required.',
    ErrorMessages.LAST_NAME_REQUIRED: 'Employee creation was rejected because last name is required.',
    ErrorMessages.EMPLOYEE_MINIMUM_AGE: 'Employee operation was rejected because the minimum age requirement was not met.',
    ErrorMessages.ADMIN_ROLE_RESTRICTED: 'Employee role operation was rejected because the admin role is restricted.',
    ErrorMessages.SUPERUSER_RESTRICTED: 'Employee operation was rejected because superuser access is restricted.',
    ErrorMessages.SINGLE_SUPERUSER: 'Employee operation was rejected because only one superuser is permitted.',
    ErrorMessages.ADMIN_EMAIL_RESTRICTED: 'Employee operation was rejected because the admin email is reserved.',
    ErrorMessages.EMPLOYEE_ALREADY_INACTIVE: 'Employee deactivation was rejected because the employee is already inactive.',
    ErrorMessages.ADMIN_DEACTIVATE_RESTRICTED: 'Employee deactivation was rejected because the administrator cannot be deactivated.',
    ErrorMessages.ADMIN_ROLE_REMOVE_RESTRICTED: 'Employee role removal was rejected because the admin role is protected.',
    ErrorMessages.ROLE_ALREADY_ASSIGNED: 'Employee role assignment was rejected because the role is already assigned.',
    ErrorMessages.ROLE_NOT_ASSIGNED: 'Employee role removal was rejected because the role is not assigned.',
    ErrorMessages.INVALID_ROLE: 'Employee role operation was rejected because the requested role is invalid.',
    ErrorMessages.CONTRIBUTION_ALREADY_CANCELLED: 'Contribution cancellation was rejected because it is already cancelled.',
    ErrorMessages.CANCELLATION_REASON_REQUIRED: 'Contribution cancellation was rejected because a reason is required.',
}


def _drf_failure_description(exc, status_code, operation):
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return f'{operation} failed because authentication was missing or invalid.', 'authentication'
    if isinstance(exc, PermissionDenied):
        return f'{operation} was rejected because the actor lacks permission.', 'permission_denied'
    if isinstance(exc, ValidationError):
        return f'{operation} was rejected because request validation failed.', 'validation'
    if isinstance(exc, NotFound) or status_code == ErrorStatus.NOT_FOUND:
        return f'{operation} failed because the requested resource was not found.', 'not_found'
    if isinstance(exc, MethodNotAllowed):
        return f'{operation} was rejected because the HTTP method is not supported.', 'method_not_allowed'
    return f'{operation} failed with an HTTP client error.', 'client_error'


class ProjectException(Exception):
    """Generic project exception used by all application code."""

    status_code = ErrorStatus.BAD_REQUEST
    default_detail = ErrorMessages.REQUEST_FAILED
    default_code = 'project_error'

    def __init__(self, detail=None, *, status_code=None, code=None):
        self.detail = detail if detail is not None else self.default_detail
        self.status_code = status_code or self.status_code
        self.code = code or self.default_code
        super().__init__(self.detail)


def _message_from_data(data):
    if isinstance(data, dict) and 'detail' in data:
        return str(data['detail'])
    if isinstance(data, dict) and data:
        field, messages = next(iter(data.items()))
        if isinstance(messages, list) and messages:
            return f'{field}: {messages[0]}'
        return f'{field}: {messages}'
    if isinstance(data, list) and data:
        return str(data[0])
    return ErrorMessages.REQUEST_FAILED


def common_exception_handler(exc, context):
    if isinstance(exc, ProjectException):
        request = context.get('request')
        actor = getattr(request, 'user', None)
        operation, event_prefix = get_api_operation(request) if request else ('API request', 'api.request')
        detail_message = (
            PROJECT_DETAIL_LOG_MESSAGES.get(exc.detail)
            if isinstance(exc.detail, str)
            else None
        )
        log_message = PROJECT_ERROR_LOG_MESSAGES.get(exc.code) or detail_message or (
            f'{operation} was rejected by an application business rule.'
        )
        logger.warning(
            '%s event=%s.failed reason=business_rule code=%s status=%s',
            log_message,
            event_prefix,
            exc.code,
            exc.status_code,
            extra={'actor_key': get_log_actor_key(actor)},
        )
        detail = exc.detail
        errors = detail if isinstance(detail, dict) else {'detail': str(detail)}
        return Response(
            {
                'success': False,
                'message': STATUS_MESSAGES.get(exc.status_code, ErrorMessages.REQUEST_FAILED),
                'errors': errors,
                'status_code': exc.status_code,
            },
            status=exc.status_code,
        )

    response = drf_exception_handler(exc, context)

    if response is not None:
        if response.status_code >= 400:
            request = context.get('request')
            operation, event_prefix = get_api_operation(request) if request else ('API request', 'api.request')
            description, failure = _drf_failure_description(
                exc,
                response.status_code,
                operation,
            )
            logger.warning(
                '%s event=%s.failed reason=%s exception=%s status=%s',
                description,
                event_prefix,
                failure,
                exc.__class__.__name__,
                response.status_code,
                extra={'actor_key': get_log_actor_key(getattr(request, 'user', None))},
            )
        data = response.data
        message = STATUS_MESSAGES.get(
            response.status_code,
            _message_from_data(data),
        )
        errors = None if isinstance(data, dict) and 'detail' in data else data
        response.data = {
            'success': False,
            'message': message,
            'errors': errors,
            'status_code': response.status_code,
        }
        return response

    request = context.get('request')
    operation, event_prefix = get_api_operation(request) if request else ('API request', 'api.request')
    logger.exception(
        '%s failed because an unexpected server error occurred. '
        'event=%s.failed reason=server_error exception=%s',
        operation,
        event_prefix,
        exc.__class__.__name__,
        exc_info=exc,
        extra={'actor_key': get_log_actor_key(getattr(request, 'user', None))},
    )
    return Response(
        {
            'success': False,
            'message': ErrorMessages.UNEXPECTED_ERROR,
            'errors': None,
            'status_code': ErrorStatus.INTERNAL_SERVER_ERROR,
        },
        status=ErrorStatus.INTERNAL_SERVER_ERROR,
    )