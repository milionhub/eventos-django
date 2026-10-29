from django.urls import path

from apps.ticketing import views

urlpatterns = [
    path("", views.ReservationCreateView.as_view(), name="reservations"),
    path(
        "<uuid:reservation_id>/cancel/",
        views.ReservationCancelView.as_view(),
        name="reservation-cancel",
    ),
]

# Mounted under me/tickets/
my_ticket_urlpatterns = [
    path("", views.MyTicketListView.as_view(), name="my-tickets"),
    path("<uuid:ticket_id>/", views.MyTicketDetailView.as_view(), name="my-ticket"),
    path("<uuid:ticket_id>/qr.svg", views.MyTicketQRView.as_view(), name="my-ticket-qr"),
]

# Mounted under organizations/<org_slug>/events/<event_id>/
attendee_urlpatterns = [
    path("reservations/", views.AttendeeListView.as_view(), name="attendees"),
    path(
        "reservations/<uuid:reservation_id>/cancel/",
        views.AttendeeCancelView.as_view(),
        name="attendee-cancel",
    ),
    path("attendees.csv", views.AttendeeExportView.as_view(), name="attendees-csv"),
]
