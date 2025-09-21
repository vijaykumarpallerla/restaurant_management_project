from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Rider, Driver
from django.db import transaction

class RiderRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for Rider registration.
    Handles the creation of a User and a related Rider profile.
    """
    # The password field is write-only for security reasons.
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = Rider
        # Fields to be validated and used from the request payload.
        fields = ['phone_number', 'preferred_payment_method', 'default_pickup_location']

    def create(self, validated_data):
        """
        Overrides the default create method to handle the creation of both
        the User and the Rider instance within a single database transaction.
        """
        # Extract user data from the initial request data, not validated_data.
        user_data = self.context['request'].data
        
        # Ensure the transaction is atomic: if one object fails, all changes are rolled back.
        with transaction.atomic():
            # Create the User object first.
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password']
            )
            
            # Create the Rider profile linked to the new user.
            rider = Rider.objects.create(user=user, **validated_data)
            
        return rider
        
    def to_representation(self, instance):
        """
        Customize the output representation to include user details.
        """
        response = super().to_representation(instance)
        # Add user's username and email to the response for confirmation.
        response['username'] = instance.user.username
        response['email'] = instance.user.email
        return response


class DriverRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for Driver registration.
    Handles creating a User and a linked Driver profile.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = Driver
        # Fields specific to the Driver model to be included in registration.
        fields = ['phone_number', 'license_number', 'vehicle_make', 'vehicle_model', 'license_plate']

    def create(self, validated_data):
        """
        Creates a User and a Driver instance atomically.
        """
        user_data = self.context['request'].data
        
        with transaction.atomic():
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password']
            )
            
            # Create the Driver profile.
            driver = Driver.objects.create(user=user, **validated_data)
            
        return driver
        
    def to_representation(self, instance):
        """
        Customize the API response to include basic user info.
        """
        response = super().to_representation(instance)
        response['username'] = instance.user.username
        response['email'] = instance.user.email
        return response
