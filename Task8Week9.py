
#models.py


from django.db import models
from django.contrib.auth.models import User


class Ride(models.Model):
    """
    Represents a single ride request and its lifecycle.
    """
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('ACCEPTED', 'Accepted'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    rider = models.ForeignKey('Rider', on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='REQUESTED')
    
    created_at = models.DateTimeField(auto_now_add=True) # Timestamp when the ride was requested
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride from {self.pickup_address} to {self.dropoff_address} ({self.status})"






#settings.py

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,  # Sets the default number of items per page
}




# serializers.py

from .models import Ride

class RideHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for displaying ride history for both riders and drivers.
    """
    # Use SerializerMethodField to get the username for a cleaner output
    rider = serializers.CharField(source='rider.user.username', read_only=True)
    driver = serializers.SerializerMethodField()
    
    # Rename 'created_at' to 'requested_at' in the API output for clarity
    requested_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Ride
        fields = [
            'id', 
            'pickup_address', 
            'dropoff_address', 
            'status', 
            'requested_at',
            'rider',
            'driver'
        ]

    def get_driver(self, obj):
        """
        Return the driver's username if a driver is assigned, otherwise return null.
        """
        if obj.driver and obj.driver.user:
            return obj.driver.user.username
        return None




# views.py
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Ride
from .serializers import RideHistorySerializer


class RiderHistoryView(ListAPIView):
    """
    API endpoint to view the ride history for the logged-in rider.
    Returns paginated results of completed or cancelled rides.
    """
    serializer_class = RideHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the rides for
        the currently authenticated user.
        """
        user = self.request.user
        # Filter rides where the rider's user is the current user and
        # the status is either COMPLETED or CANCELLED.
        return Ride.objects.filter(
            rider__user=user,
            status__in=['COMPLETED', 'CANCELLED']
        ).order_by('-created_at')


class DriverHistoryView(ListAPIView):
    """
    API endpoint to view the ride history for the logged-in driver.
    Returns paginated results of completed or cancelled rides.
    """
    serializer_class = RideHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the rides for
        the currently authenticated driver.
        """
        user = self.request.user
        # Filter rides where the driver's user is the current user and
        # the status is either COMPLETED or CANCELLED.
        return Ride.objects.filter(
            driver__user=user,
            status__in=['COMPLETED', 'CANCELLED']
        ).order_by('-created_at')



#urls.py 

from django.urls import path
from .views import (
    rider_registration_view, 
    driver_registration_view,
    RiderHistoryView,
    DriverHistoryView
)

urlpatterns = [
    # Registration endpoints
    path('register/rider/', rider_registration_view, name='register-rider'),
    path('register/driver/', driver_registration_view, name='register-driver'),
    
    # History endpoints
    path('rider/history/', RiderHistoryView.as_view(), name='rider-history'),
    path('driver/history/', DriverHistoryView.as_view(), name='driver-history'),
]