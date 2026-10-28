from django.urls import path

from apps.events import views

# Mounted under organizations/<org_slug>/events/
urlpatterns = [
    path("", views.EventListView.as_view(), name="events"),
    path("<int:event_id>/", views.EventDetailView.as_view(), name="event"),
    path("<int:event_id>/publish/", views.EventPublishView.as_view(), name="event-publish"),
    path("<int:event_id>/cancel/", views.EventCancelView.as_view(), name="event-cancel"),
    path("<int:event_id>/image/", views.EventImageView.as_view(), name="event-image"),
    path(
        "<int:event_id>/ticket-types/",
        views.TicketTypeListView.as_view(),
        name="ticket-types",
    ),
    path(
        "<int:event_id>/ticket-types/<int:ticket_type_id>/",
        views.TicketTypeDetailView.as_view(),
        name="ticket-type",
    ),
    path("<int:event_id>/staff/", views.StaffListView.as_view(), name="staff"),
    path(
        "<int:event_id>/staff/<int:assignment_id>/",
        views.StaffDetailView.as_view(),
        name="staff-assignment",
    ),
]

# Mounted under public/
public_urlpatterns = [
    path("events/", views.PublicEventListView.as_view(), name="public-events"),
    path("events/<slug:slug>/", views.PublicEventDetailView.as_view(), name="public-event"),
]
