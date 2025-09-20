from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

# A validator for standard phone numbers.
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

class Rider(models.Model):
    """
    Represents a Rider in the ride-sharing application.
    This model extends the built-in Django User model to store rider-specific information.
    """
    # Each Rider profile is linked to a single User account.
    # If the User is deleted, the Rider profile is also deleted (CASCADE).
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    
    # Rider-specific fields
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    profile_photo = models.ImageField(upload_to='riders/profile_photos/', blank=True, null=True)
    
    # Choices for the preferred payment method
    PAYMENT_CHOICES = [
        ('CARD', 'Credit/Debit Card'),
        ('CASH', 'Cash'),
        ('WALLET', 'Digital Wallet'),
    ]
    preferred_payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default='CARD'
    )
    
    # A text field to store a default or favorite pickup location.
    # Can be left blank if the user hasn't set one.
    default_pickup_location = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps for tracking when the record was created or last updated.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """String representation of the Rider model, using the associated user's username."""
        return f"Rider: {self.user.username}"


class Driver(models.Model):
    """
    Represents a Driver in the ride-sharing application.
    This model also extends the User model for driver-specific data.
    """
    # Link to the built-in User model.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    
    # Driver-specific fields
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    profile_photo = models.ImageField(upload_to='drivers/profile_photos/', blank=True, null=True)
    license_number = models.CharField(max_length=50, unique=True)
    
    # Vehicle Information
    vehicle_make = models.CharField(max_length=50, help_text="e.g., Toyota, Honda")
    vehicle_model = models.CharField(max_length=50, help_text="e.g., Camry, Civic")
    license_plate = models.CharField(max_length=20, unique=True, help_text="Vehicle's number plate")

    # Real-time status and location
    is_available = models.BooleanField(default=False, help_text="Is the driver currently available for rides?")
    # Using DecimalField for precision in geographic coordinates.
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """String representation of the Driver model."""
        return f"Driver: {self.user.username} ({self.license_plate})"
