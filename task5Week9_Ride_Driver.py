# models.py


from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator


class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    phone_number = models.CharField(validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')], max_length=17, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"Rider: {self.user.username}"

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    phone_number = models.CharField(validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')], max_length=17, unique=True)
    license_plate = models.CharField(max_length=20, unique=True)
    is_available = models.BooleanField(default=False)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"Driver: {self.user.username} ({self.license_plate})"

class Ride(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('ACCEPTED', 'Accepted'), # You can use this status between REQUESTED and ONGOING if needed
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    
    # NEW: Latitude and Longitude fields for precision
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='REQUESTED')
    
    # Renamed for clarity
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride from {self.pickup_address} to {self.dropoff_address} ({self.status})"

# --- Existing Feedback Model ---
# ... (Keep the RideFeedback model as is) ...
class RideFeedback(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='feedback')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    is_driver_feedback = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('ride', 'submitted_by')



     
#permissions.py

from rest_framework.permissions import BasePermission

class IsDriverUser(BasePermission):
    message = "You are not authorized as a driver."
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'driver_profile')

class IsRiderUser(BasePermission):
    """
    Custom permission to only allow users with a rider profile to access an endpoint.
    """
    message = "You are not authorized as a rider."
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'rider_profile')



# serializers.py


from rest_framework import serializers
from .models import Rider, Driver, Ride

class RideRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for riders to create a new ride request.
    """
    class Meta:
        model = Ride
        fields = [
            'pickup_address', 'dropoff_address',
            'pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng'
        ]
        # The rider and status are set automatically in the view, not by the user.
        read_only_fields = ['rider', 'driver', 'status']

class AvailableRidesSerializer(serializers.ModelSerializer):
    """
    Serializer to display key information about available rides to drivers.
    """
    rider_username = serializers.CharField(source='rider.user.username', read_only=True)

    class Meta:
        model = Ride
        fields = [
            'id', 'rider_username', 'pickup_address', 'dropoff_address',
            'pickup_lat', 'pickup_lng', 'requested_at'
        ]

#views.py

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Ride
from .serializers import RideRequestSerializer, AvailableRidesSerializer
from .permissions import IsRiderUser, IsDriverUser



class RideRequestView(generics.CreateAPIView):
    """
    API endpoint for an authenticated rider to request a new ride.
    POST /api/ride/request/
    """
    queryset = Ride.objects.all()
    serializer_class = RideRequestSerializer
    permission_classes = [IsAuthenticated, IsRiderUser]

    def perform_create(self, serializer):
        """
        Automatically associate the ride request with the logged-in rider.
        """
        serializer.save(rider=self.request.user.rider_profile)

class AvailableRidesView(generics.ListAPIView):
    """
    API endpoint for authenticated drivers to see all available ride requests.
    GET /api/ride/available/
    """
    queryset = Ride.objects.filter(status='REQUESTED', driver__isnull=True).order_by('-requested_at')
    serializer_class = AvailableRidesSerializer
    permission_classes = [IsAuthenticated, IsDriverUser]

class AcceptRideView(APIView):
    """
    API endpoint for an authenticated driver to accept a ride request.
    POST /api/ride/accept/<id>/
    """
    permission_classes = [IsAuthenticated, IsDriverUser]

    def post(self, request, id, *args, **kwargs):
        # Use a database transaction to handle the acceptance process atomically.
        # 
        try:
            with transaction.atomic():
                # Lock the ride object to prevent race conditions (two drivers accepting at once).
                ride = Ride.objects.select_for_update().get(id=id)

                # Rule 1: Check if the ride is still available.
                if ride.status != 'REQUESTED' or ride.driver is not None:
                    return Response(
                        {"error": "This ride is no longer available."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Assign the driver and update the status.
                ride.driver = request.user.driver_profile
                ride.status = 'ONGOING' # Or 'ACCEPTED' if you have an intermediate step
                ride.save()

                return Response(
                    {"message": "Ride accepted successfully."},
                    status=status.HTTP_200_OK
                )
        except Ride.DoesNotExist:
            return Response({"error": "Ride not found."}, status=status.HTTP_404_NOT_FOUND)



#urls.py


from django.urls import path
from .views import (
    # ... other views
    RideRequestView,
    AvailableRidesView,
    AcceptRideView,
)

urlpatterns = [
    # ... other url patterns
    
    # --- NEW: Ride Booking Flow Endpoints ---
    # URL for riders to request a ride
    path('ride/request/', RideRequestView.as_view(), name='ride-request'),
    
    # URL for drivers to see available rides
    path('ride/available/', AvailableRidesView.as_view(), name='ride-available'),
    
    # URL for a driver to accept a ride (e.g., /api/ride/accept/42/)
    path('ride/accept/<int:id>/', AcceptRideView.as_view(), name='ride-accept'),
]