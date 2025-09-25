
# models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

# A validator for standard phone numbers.
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    profile_photo = models.ImageField(upload_to='riders/profile_photos/', blank=True, null=True)
    PAYMENT_CHOICES = [
        ('CARD', 'Credit/Debit Card'),
        ('CASH', 'Cash'),
        ('WALLET', 'Digital Wallet'),
    ]
    preferred_payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='CARD')
    default_pickup_location = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rider: {self.user.username}"


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    profile_photo = models.ImageField(upload_to='drivers/profile_photos/', blank=True, null=True)
    license_number = models.CharField(max_length=50, unique=True)
    vehicle_make = models.CharField(max_length=50, help_text="e.g., Toyota, Honda")
    vehicle_model = models.CharField(max_length=50, help_text="e.g., Camry, Civic")
    license_plate = models.CharField(max_length=20, unique=True, help_text="Vehicle's number plate")
    is_available = models.BooleanField(default=False, help_text="Is the driver currently available for rides?")
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Driver: {self.user.username} ({self.license_plate})"


class Ride(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('ACCEPTED', 'Accepted'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='REQUESTED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride from {self.pickup_address} to {self.dropoff_address} ({self.status})"


class RideFeedback(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='feedback')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    is_driver_feedback = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ride', 'submitted_by')

    def __str__(self):
        feedback_from = "Driver" if self.is_driver_feedback else "Rider"
        return f"Feedback for Ride {self.ride.id} from {feedback_from} ({self.rating} stars)"



# permissions.py

from rest_framework.permissions import BasePermission

class IsDriverUser(BasePermission):
    """
    Custom permission to only allow users with a driver profile to access an endpoint.
    """
    message = "You are not authorized as a driver."

    def has_permission(self, request, view):
        return request.user and hasattr(request.user, 'driver_profile')



# serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Rider, Driver, Ride, RideFeedback
from django.db import transaction

# --- Registration Serializers ---
class RiderRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    class Meta:
        model = Rider
        fields = ['phone_number', 'preferred_payment_method', 'default_pickup_location']
    def create(self, validated_data):
        user_data = self.context['request'].data
        with transaction.atomic():
            user = User.objects.create_user(username=user_data['username'], email=user_data['email'], password=user_data['password'])
            rider = Rider.objects.create(user=user, **validated_data)
        return rider
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['username'] = instance.user.username
        response['email'] = instance.user.email
        return response

class DriverRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    class Meta:
        model = Driver
        fields = ['phone_number', 'license_number', 'vehicle_make', 'vehicle_model', 'license_plate']
    def create(self, validated_data):
        user_data = self.context['request'].data
        with transaction.atomic():
            user = User.objects.create_user(username=user_data['username'], email=user_data['email'], password=user_data['password'])
            driver = Driver.objects.create(user=user, **validated_data)
        return driver
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['username'] = instance.user.username
        response['email'] = instance.user.email
        return response

# --- Ride History Serializer ---
class RideHistorySerializer(serializers.ModelSerializer):
    rider = serializers.CharField(source='rider.user.username', read_only=True)
    driver = serializers.SerializerMethodField()
    requested_at = serializers.DateTimeField(source='created_at', read_only=True)
    class Meta:
        model = Ride
        fields = ['id', 'pickup_address', 'dropoff_address', 'status', 'requested_at', 'rider', 'driver']
    def get_driver(self, obj):
        if obj.driver and obj.driver.user:
            return obj.driver.user.username
        return None

# --- Ride Feedback Serializer ---
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

# --- Location Tracking Serializers ---
class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)

class TrackRideSerializer(serializers.ModelSerializer):
    driver_latitude = serializers.DecimalField(source='driver.current_latitude', max_digits=9, decimal_places=6, read_only=True)
    driver_longitude = serializers.DecimalField(source='driver.current_longitude', max_digits=9, decimal_places=6, read_only=True)
    class Meta:
        model = Ride
        fields = ['driver_latitude', 'driver_longitude']

# views.py

from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Ride
from .serializers import (
    RiderRegistrationSerializer, DriverRegistrationSerializer, RideHistorySerializer,
    RideFeedbackSerializer, LocationUpdateSerializer, TrackRideSerializer
)
from .permissions import IsDriverUser

# --- Registration Views ---
@api_view(['POST'])
@permission_classes([AllowAny])
def rider_registration_view(request):
    if request.method == 'POST':
        serializer = RiderRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def driver_registration_view(request):
    if request.method == 'POST':
        serializer = DriverRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Ride History Views ---
class RiderHistoryView(generics.ListAPIView):
    serializer_class = RideHistorySerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        return Ride.objects.filter(rider__user=user, status__in=['COMPLETED', 'CANCELLED']).order_by('-created_at')

class DriverHistoryView(generics.ListAPIView):
    serializer_class = RideHistorySerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        return Ride.objects.filter(driver__user=user, status__in=['COMPLETED', 'CANCELLED']).order_by('-created_at')

# --- Ride Feedback View (You will create this view next) ---
# Placeholder for RideFeedbackView
# Example:
# class RideFeedbackView(generics.CreateAPIView):
#     queryset = RideFeedback.objects.all()
#     serializer_class = RideFeedbackSerializer
#     permission_classes = [IsAuthenticated]
#     def get_serializer_context(self):
#         context = super().get_serializer_context()
#         ride_id = self.kwargs.get('ride_id')
#         context['ride'] = get_object_or_404(Ride, id=ride_id)
#         context['request'] = self.request
#         return context

# --- Location Tracking Views ---
class UpdateLocationView(APIView):
    permission_classes = [IsAuthenticated, IsDriverUser]
    def post(self, request, *args, **kwargs):
        serializer = LocationUpdateSerializer(data=request.data)
        if serializer.is_valid():
            driver_profile = request.user.driver_profile
            driver_profile.current_latitude = serializer.validated_data['latitude']
            driver_profile.current_longitude = serializer.validated_data['longitude']
            driver_profile.save()
            return Response({"status": "Location updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TrackRideView(generics.RetrieveAPIView):
    queryset = Ride.objects.all()
    serializer_class = TrackRideSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    def get_object(self):
        ride = super().get_object()
        if ride.rider.user != self.request.user:
            self.permission_denied(self.request, message="You are not authorized to track this ride.")
        if ride.status != 'ONGOING':
            self.permission_denied(self.request, message="Tracking is only available for ongoing rides.")
        return ride


# urls.py

from django.urls import path
from .views import (
    rider_registration_view,
    driver_registration_view,
    RiderHistoryView,
    DriverHistoryView,
    UpdateLocationView,
    TrackRideView,
    # RideFeedbackView # Uncomment when you create this view
)

urlpatterns = [
    # Registration endpoints
    path('register/rider/', rider_registration_view, name='register-rider'),
    path('register/driver/', driver_registration_view, name='register-driver'),

    # History endpoints
    path('rider/history/', RiderHistoryView.as_view(), name='rider-history'),
    path('driver/history/', DriverHistoryView.as_view(), name='driver-history'),

    # Feedback endpoint (You will complete this URL pattern)
    # path('ride/feedback/<int:ride_id>/', RideFeedbackView.as_view(), name='ride-feedback'),

    # Location tracking endpoints
    path('ride/update-location/', UpdateLocationView.as_view(), name='update-location'),
    path('ride/track/<int:id>/', TrackRideView.as_view(), name='track-ride'),
]