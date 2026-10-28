from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import ErrorSerializer
from apps.organizations import selectors, services
from apps.organizations.mixins import ALL_ROLES, OrganizationScopedMixin
from apps.organizations.models import Membership
from apps.organizations.serializers import (
    AddMemberSerializer,
    ChangeRoleSerializer,
    MemberSerializer,
    MyOrganizationSerializer,
    OrganizationSerializer,
)

OWNER_ONLY = frozenset({Membership.Role.OWNER})

# Lists here are bounded (a user's organizations, an organization's members) and the
# screens show them whole, so they are not paginated.


class OrganizationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="organizations_list", responses=MyOrganizationSerializer(many=True))
    def get(self, request: Request) -> Response:
        memberships = selectors.memberships_for_user(request.user)
        return Response(MyOrganizationSerializer(memberships, many=True).data)

    @extend_schema(
        operation_id="organizations_create",
        request=OrganizationSerializer,
        responses={201: MyOrganizationSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = services.create_organization(user=request.user, **serializer.validated_data)
        data = {"organization": organization, "role": Membership.Role.OWNER}
        return Response(MyOrganizationSerializer(data).data, status=status.HTTP_201_CREATED)


class OrganizationDetailView(OrganizationScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ALL_ROLES, "PATCH": OWNER_ONLY}

    @extend_schema(operation_id="organizations_retrieve", responses=MyOrganizationSerializer)
    def get(self, request: Request, org_slug: str) -> Response:
        return Response(MyOrganizationSerializer(self.membership).data)

    @extend_schema(
        operation_id="organizations_update",
        request=OrganizationSerializer,
        responses=MyOrganizationSerializer,
    )
    def patch(self, request: Request, org_slug: str) -> Response:
        serializer = OrganizationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_organization(organization=self.organization, **serializer.validated_data)
        return Response(MyOrganizationSerializer(self.membership).data)


class MemberListView(OrganizationScopedMixin, APIView):
    """RN-05: only the OWNER manages members."""

    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": OWNER_ONLY, "POST": OWNER_ONLY}

    @extend_schema(operation_id="members_list", responses=MemberSerializer(many=True))
    def get(self, request: Request, org_slug: str) -> Response:
        return Response(MemberSerializer(selectors.members_of(self.organization), many=True).data)

    @extend_schema(
        operation_id="members_create",
        request=AddMemberSerializer,
        responses={201: MemberSerializer, 400: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, org_slug: str) -> Response:
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.add_member(
            organization=self.organization, **serializer.validated_data
        )
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class MemberDetailView(OrganizationScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"PATCH": OWNER_ONLY, "DELETE": OWNER_ONLY}

    def get_membership(self, member_id: int) -> Membership:
        # Filtered by the organization from the URL: another organization's member is a 404.
        return get_object_or_404(selectors.members_of(self.organization), pk=member_id)

    @extend_schema(
        operation_id="members_update",
        request=ChangeRoleSerializer,
        responses={200: MemberSerializer, 409: ErrorSerializer},
    )
    def patch(self, request: Request, org_slug: str, member_id: int) -> Response:
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.change_member_role(
            membership=self.get_membership(member_id), **serializer.validated_data
        )
        return Response(MemberSerializer(membership).data)

    @extend_schema(
        operation_id="members_destroy",
        responses={204: OpenApiResponse(), 409: ErrorSerializer},
    )
    def delete(self, request: Request, org_slug: str, member_id: int) -> Response:
        services.remove_member(membership=self.get_membership(member_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
