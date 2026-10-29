from django.urls import path

from apps.checkin import views

# Mounted under checkin/
urlpatterns = [
    path("events/", views.CheckinEventListView.as_view(), name="checkin-events"),
    path("events/<int:event_id>/scan/", views.ScanView.as_view(), name="checkin-scan"),
    path(
        "events/<int:event_id>/activity/",
        views.CheckinActivityView.as_view(),
        name="checkin-activity",
    ),
]

# Mounted under organizations/<org_slug>/
organizer_urlpatterns = [
    path("stats/", views.OrganizationStatsView.as_view(), name="organization-stats"),
    path("events/<int:event_id>/stats/", views.EventStatsView.as_view(), name="event-stats"),
]
