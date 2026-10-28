from django.urls import path

from apps.events import views

# Mounted under organizations/<org_slug>/events/
urlpatterns = [
    path("", views.EventListView.as_view(), name="events"),
    path("<int:event_id>/", views.EventDetailView.as_view(), name="event"),
    path("<int:event_id>/publish/", views.EventPublishView.as_view(), name="event-publish"),
    path("<int:event_id>/cancel/", views.EventCancelView.as_view(), name="event-cancel"),
]
