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
