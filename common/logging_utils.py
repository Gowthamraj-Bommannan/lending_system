import hashlib
import hmac
import logging
from contextvars import ContextVar

from django.conf import settings


request_id_context = ContextVar('request_id', default='-')


class RequestContextFilter(logging.Filter):
    """Attach request correlation data to every configured log record."""

    def filter(self, record):
        if not hasattr(record, 'request_id'):
            record.request_id = request_id_context.get()
        if not hasattr(record, 'actor_key'):
            record.actor_key = '-'
        return True


def get_log_actor_key(user):
    """Return a stable pseudonymous key; never put employee identifiers in logs."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return '-'
    identity = f'{user._meta.label_lower}:{user.pk}'.encode()
    key = str(settings.SECRET_KEY).encode()
    return hmac.new(key, identity, hashlib.sha256).hexdigest()[:16]