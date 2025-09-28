
#models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator



class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    phone_number = models.CharField(validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')], max_length=17, unique=True)
    def __str__(self): return f"Rider: {self.user.username}"

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    phone_number = models.CharField(validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')], max_length=17, unique=True)
    license_plate = models.CharField(max_length=20, unique=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    def __str__(self): return f"Driver: {self.user.username} ({self.license_plate})"

class Ride(models.Model):
    STATUS_CHOICES = [('REQUESTED', 'Requested'), ('ONGOING', 'Ongoing'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')]
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='REQUESTED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"Ride from {self.pickup_address} to {self.dropoff_address} ({self.status})"

class RideFeedback(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='feedback')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    is_driver_feedback = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('ride', 'submitted_by')
    def __str__(self):
        feedback_from = "Driver" if self.is_driver_feedback else "Rider"
        return f"Feedback for Ride {self.ride.id} from {feedback_from} ({self.rating} stars)"


#permissions.py

from rest_framework.permissions import BasePermission

class IsDriverUser(BasePermission):
    message = "You are not authorized as a driver."
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'driver_profile')


# serializers.py


from rest_framework import serializers
from .models import RideFeedback, Ride

class RideFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideFeedback
        fields = ['rating', 'comment']
        read_only_fields = ['id', 'submitted_at', 'submitted_by', 'is_driver_feedback']

    def validate(self, data):
        ride = self.context['ride']
        user = self.context['request'].user
        if ride.status != 'COMPLETED':
            raise serializers.ValidationError("Feedback can only be submitted for completed rides.")
        is_rider = (ride.rider.user == user)
        is_driver = (ride.driver and ride.driver.user == user)
        if not is_rider and not is_driver:
            raise serializers.ValidationError("You are not authorized to submit feedback for this ride.")
        if RideFeedback.objects.filter(ride=ride, submitted_by=user).exists():
            raise serializers.ValidationError("You have already submitted feedback for this ride.")
        return data

    def create(self, validated_data):
        ride = self.context['ride']
        user = self.context['request'].user
        is_from_driver = (ride.driver and ride.driver.user == user)
        feedback = RideFeedback.objects.create(ride=ride, submitted_by=user, is_driver_feedback=is_from_driver, **validated_data)
        return feedback



#views.py


from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Ride, RideFeedback
from .serializers import RideFeedbackSerializer


class RideFeedbackView(generics.CreateAPIView):
    """
    API endpoint for submitting feedback for a completed ride.
    Accessible via: POST /api/ride/feedback/<ride_id>/
    """
    queryset = RideFeedback.objects.all()
    serializer_class = RideFeedbackSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        """
        This method is crucial. It passes extra information (the ride object
        and the request) from the view to the serializer. The serializer's
        validation logic depends on this context to check permissions and rules.
        """
        context = super().get_serializer_context()
        ride_id = self.kwargs.get('id')
        context['ride'] = get_object_or_404(Ride, id=ride_id)
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """
        Overrides the default create method to return a custom success message
        instead of the full serialized object.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # 
        return Response(
            {"message": "Feedback submitted successfully."},
            status=status.HTTP_201_CREATED
        )


#urls.py

from django.urls import path
from .views import (
    # ... other views
    RideFeedbackView, # <-- IMPORT NEW VIEW
)

urlpatterns = [
    
    path('ride/feedback/<int:id>/', RideFeedbackView.as_view(), name='ride-feedback'),
]