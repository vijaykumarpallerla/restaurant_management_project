# models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

# ...
class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    # ... other fields
    def __str__(self): return f"Rider: {self.user.username}"

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    # ... other fields
    def __str__(self): return f"Driver: {self.user.username} ({self.license_plate})"

class Ride(models.Model):
    STATUS_CHOICES = [('REQUESTED', 'Requested'), ('ONGOING', 'Ongoing'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')]
    PAYMENT_STATUS_CHOICES = [('UNPAID', 'Unpaid'), ('PAID', 'Paid')]
    PAYMENT_METHOD_CHOICES = [('CASH', 'Cash'), ('CARD', 'Card'), ('WALLET', 'Wallet')]

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='REQUESTED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"Ride from {self.pickup_address} to {self.dropoff_address} ({self.status}, {self.payment_status})"


class RideFeedback(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='feedback')
    # ... other fields
    def __str__(self):
        feedback_from = "Driver" if self.is_driver_feedback else "Rider"
        return f"Feedback for Ride {self.ride.id} from {feedback_from} ({self.rating} stars)"


# permissions.py

from rest_framework.permissions import BasePermission

class IsDriverUser(BasePermission):
    message = "You are not authorized as a driver."
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'driver_profile')


# serializers.py

from rest_framework import serializers
from .models import Ride


class RidePaymentSerializer(serializers.Serializer):
    """
    Serializer to validate the payment method provided in the payment request.
    The payment status is handled by the view, not taken from user input.
    """
    payment_method = serializers.ChoiceField(choices=Ride.PAYMENT_METHOD_CHOICES)


#views.py

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Ride
from .serializers import RidePaymentSerializer


class MarkAsPaidView(APIView):
    """
    API endpoint for a rider or driver to mark a ride as PAID.
    Accessible via: POST /api/ride/payment/<id>/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RidePaymentSerializer

    def post(self, request, id, *args, **kwargs):
        ride = get_object_or_404(Ride, id=id)

        # Security Rule: Ensure the user is either the rider or the driver of this ride.
        is_rider = ride.rider.user == request.user
        is_driver = ride.driver and ride.driver.user == request.user
        if not is_rider and not is_driver:
            return Response(
                {"error": "You are not authorized to perform this action on this ride."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validation Rule 1: Ride must be COMPLETED.
        if ride.status != 'COMPLETED':
            return Response(
                {"error": "Ride is not completed yet. Payment can only be marked for completed rides."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validation Rule 2: Ride must not already be PAID.
        if ride.payment_status == 'PAID':
            return Response(
                {"error": "This ride has already been marked as paid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # If data is valid, update the ride instance.
            ride.payment_status = 'PAID'
            ride.payment_method = serializer.validated_data['payment_method']
            ride.save()

            # 
            return Response({
                "message": "Payment marked as complete.",
                "status": ride.payment_status,
                "method": ride.payment_method
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# urls.py

from django.urls import path
from .views import (
    MarkAsPaidView, # <-- IMPORT NEW VIEW
)

urlpatterns = [

    path('ride/payment/<int:id>/', MarkAsPaidView.as_view(), name='ride-payment'),
]