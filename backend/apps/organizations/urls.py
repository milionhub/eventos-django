from django.urls import path

from apps.organizations import views

urlpatterns = [
    path("", views.OrganizationListView.as_view(), name="organizations"),
    path("<slug:org_slug>/", views.OrganizationDetailView.as_view(), name="organization"),
    path("<slug:org_slug>/members/", views.MemberListView.as_view(), name="members"),
    path(
        "<slug:org_slug>/members/<int:member_id>/",
        views.MemberDetailView.as_view(),
        name="member",
    ),
]
