import logging

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from common.logging_utils import get_log_actor_key


logger = logging.getLogger(__name__)


class EmployeeTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, employee):
        token = super().get_token(employee)
        token['employee_id'] = employee.employee_id
        token['roles'] = list(employee.role_assignments.values_list('role', flat=True))
        return token

    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            logger.warning(
                'Employee login failed because the supplied credentials were not accepted. '
                'event=auth.login.failed'
            )
            raise
        logger.info(
            'Employee authentication succeeded. event=auth.login.succeeded',
            extra={'actor_key': get_log_actor_key(self.user)},
        )
        data['employee'] = {
            'employee_id': self.user.employee_id,
            'email': self.user.email,
            'roles': list(self.user.role_assignments.values_list('role', flat=True)),
        }
        return data