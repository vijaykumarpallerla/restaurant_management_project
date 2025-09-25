# models.py 
from django.conf import settings
from django.db import models

class Ride(models.Model):
    """
    Represents a ride request and its lifecycle.
    """
    class RideStatus(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested'
        ONGOING = 'ONGOING', 'Ongoing'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rides_as_rider'
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='rides_as_driver',
        null=True,
        blank=True
    )
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=RideStatus.choices,
        default=RideStatus.REQUESTED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride {self.id} - {self.status}"






# views.py 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Ride

class CompleteRideView(APIView):
    """
    API endpoint for a driver to mark a ride as completed.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id, *args, **kwargs):
        try:
            ride = Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Rule: Only drivers can complete a ride.
        if not request.user.is_driver:
            return Response(
                {"error": "Only drivers can complete a ride."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Rule: Only the driver assigned to the ride can complete it.
        if ride.driver != request.user:
            return Response(
                {"error": "You are not authorized to complete this ride."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Rule: Ride must be 'ONGOING' to be completed.
        if ride.status != Ride.RideStatus.ONGOING:
            return Response(
                {"error": f"Cannot complete a ride with status '{ride.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status and save
        ride.status = Ride.RideStatus.COMPLETED
        ride.save()

        return Response(
            {"message": "Ride marked as completed."},
            status=status.HTTP_200_OK
        )


class CancelRideView(APIView):
    """
    API endpoint for a rider to cancel a ride.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id, *args, **kwargs):
        try:
            ride = Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Rule: Only the rider who booked the ride can cancel it.
        if ride.rider != request.user:
            return Response(
                {"error": "You are not authorized to cancel this ride."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Rule: Ride can only be cancelled if it's 'REQUESTED'.
        if ride.status != Ride.RideStatus.REQUESTED:
            return Response(
                {"error": "Cannot cancel a ride that is already ongoing or completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status and save
        ride.status = Ride.RideStatus.CANCELLED
        ride.save()

        return Response(
            {"message": "Ride cancelled successfully."},
            status=status.HTTP_200_OK
        )


# urls.py 

from django.urls import path
from .views import CompleteRideView, CancelRideView

urlpatterns = [
    # ... other ride-related URLs
    path('ride/complete/<int:ride_id>/', CompleteRideView.as_view(), name='complete-ride'),
    path('ride/cancel/<int:ride_id>/', CancelRideView.as_view(), name='cancel-ride'),
]

# project/ urls.py 
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('rides.urls')), # Include your app's URLs
    # ... other includes
]
