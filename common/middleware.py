import logging
import time
import uuid

from .logging_utils import request_id_context
from .logging_utils import get_log_actor_key
from .api_log_messages import get_api_operation


logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    """Correlate requests and record concise, non-sensitive completion logs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid.uuid4().hex
        request.request_id = request_id
        context_token = request_id_context.set(request_id)
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = self.get_response(request)
            status_code = response.status_code
            response['X-Request-ID'] = request_id
            return response
        except Exception:
            logger.exception('event=request.unhandled_exception method=%s', request.method)
            raise
        finally:
            resolver_match = getattr(request, 'resolver_match', None)
            route = getattr(resolver_match, 'route', None) or 'unresolved'
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            if request.path.startswith('/api/') and status_code < 400:
                operation, event_prefix = get_api_operation(request)
                logger.info(
                    '%s completed successfully. event=%s.succeeded method=%s route=%s status=%s elapsed_ms=%s',
                    operation,
                    event_prefix,
                    request.method,
                    route,
                    status_code,
                    elapsed_ms,
                    extra={'actor_key': get_log_actor_key(getattr(request, 'user', None))},
                )
            elif request.path.startswith('/api/') and status_code >= 400 and not resolver_match:
                logger.warning(
                    'API endpoint could not be resolved. event=api.request.failed '
                    'failure=endpoint_not_found method=%s status=%s',
                    request.method,
                    status_code,
                    extra={'actor_key': get_log_actor_key(getattr(request, 'user', None))},
                )
            logger.info(
                'event=request.completed method=%s route=%s status=%s elapsed_ms=%s',
                request.method,
                route,
                status_code,
                elapsed_ms,
            )
            request_id_context.reset(context_token)