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
