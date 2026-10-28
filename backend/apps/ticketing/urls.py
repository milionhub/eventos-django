from django.urls import path

from apps.ticketing import views

urlpatterns = [
    path("", views.ReservationCreateView.as_view(), name="reservations"),
]
