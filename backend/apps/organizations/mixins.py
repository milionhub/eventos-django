from django.http import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from apps.organizations import selectors
from apps.organizations.models import Membership, Organization

Role = Membership.Role
ALL_ROLES = frozenset(Role)


class OrganizationScopedMixin:
    """For views under `organizations/<org_slug>/...` (RN-06).

    Resolves the organization from the URL through the user's own memberships, so an
    organization the user does not belong to is indistinguishable from one that does
    not exist: 404. A member whose role is not enough for the method gets 403.

    Views declare who may call each method:

        roles_by_method = {"GET": ALL_ROLES, "PATCH": {Role.OWNER}}

    and then use `self.organization` / `self.membership`, filtering every queryset by
    `self.organization`.
    """

    roles_by_method: dict[str, frozenset[str] | set[str]] = {}

    organization: Organization
    membership: Membership

    def initial(self, request: Request, *args, **kwargs) -> None:
        super().initial(request, *args, **kwargs)  # authentication, permissions, throttling
        membership = selectors.membership_for(request.user, kwargs["org_slug"])
        if membership is None:
            raise Http404
        allowed = self.roles_by_method.get(request.method, frozenset())
        if membership.role not in allowed:
            raise PermissionDenied("Tu rol en esta organización no permite esta acción.")
        self.membership = membership
        self.organization = membership.organization
