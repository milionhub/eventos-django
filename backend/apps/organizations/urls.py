from django.urls import include, path

from apps.checkin.urls import organizer_urlpatterns as checkin_organizer
from apps.organizations import views
from apps.ticketing.urls import attendee_urlpatterns as attendees

urlpatterns = [
    path("", views.OrganizationListView.as_view(), name="organizations"),
    path("<slug:org_slug>/", views.OrganizationDetailView.as_view(), name="organization"),
    path("<slug:org_slug>/members/", views.MemberListView.as_view(), name="members"),
    path(
        "<slug:org_slug>/members/<int:member_id>/",
        views.MemberDetailView.as_view(),
        name="member",
    ),
    path("<slug:org_slug>/events/", include("apps.events.urls")),
    path("<slug:org_slug>/events/<int:event_id>/", include(attendees)),
    path("<slug:org_slug>/", include(checkin_organizer)),
]
