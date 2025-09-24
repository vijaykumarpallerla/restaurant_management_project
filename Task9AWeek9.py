#models.py

from django.core.validators import MinValueValidator, MaxValueValidator


class RideFeedback(models.Model):
    """
    Stores feedback (rating and comment) for a specific ride, submitted by
    either the Rider or the Driver.
    """
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='feedback')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)

    # This boolean helps distinguish who left the feedback.
    # True = The driver is reviewing the rider.
    # False = The rider is reviewing the driver.
    is_driver_feedback = models.BooleanField()

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This is a crucial database constraint. It ensures that a user
        # (submitted_by) can only submit one feedback per ride.
        # This prevents duplicate entries at the database level.
        unique_together = ('ride', 'submitted_by')

    def __str__(self):
        feedback_from = "Driver" if self.is_driver_feedback else "Rider"
        return f"Feedback for Ride {self.ride.id} from {feedback_from} ({self.rating} stars)"




#Serializers.py 

from .models import RideFeedback, Ride


class RideFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and validating feedback for a completed ride.
    The view will provide the `ride` and `request` objects in the context.
    """
    class Meta:
        model = RideFeedback
        # The user only needs to submit a rating and an optional comment.
        fields = ['rating', 'comment']
        # These fields will be set programmatically in the view/serializer, not by user input.
        read_only_fields = ['id', 'submitted_at', 'submitted_by', 'is_driver_feedback']

    def validate(self, data):
        """
        This method is the heart of our custom validation logic. DRF calls this automatically.
        """
        # The view will pass the ride object and the request into the serializer's context.
        ride = self.context['ride']
        user = self.context['request'].user

        # Rule 1: The ride must be completed before feedback can be given.
        if ride.status != 'COMPLETED':
            raise serializers.ValidationError("Feedback can only be submitted for completed rides.")

        # Rule 2: The user submitting feedback must be the rider or the driver for this ride.
        is_rider = (ride.rider.user == user)
        # We must check if a driver is assigned before comparing the user.
        is_driver = (ride.driver and ride.driver.user == user)

        if not is_rider and not is_driver:
            # This check prevents any random authenticated user from submitting feedback.
            raise serializers.ValidationError("You are not authorized to submit feedback for this ride.")

        # Rule 3: The user must not have already submitted feedback for this specific ride.
        if RideFeedback.objects.filter(ride=ride, submitted_by=user).exists():
            raise serializers.ValidationError("You have already submitted feedback for this ride.")

        return data

    def create(self, validated_data):
        """
        Creates the RideFeedback object after all validation has passed successfully.
        """
        ride = self.context['ride']
        user = self.context['request'].user

        # Determine if the feedback is from the driver to set the boolean flag correctly.
        is_from_driver = (ride.driver and ride.driver.user == user)

        # Create the feedback instance with the validated data plus the context-derived fields.
        feedback = RideFeedback.objects.create(
            ride=ride,
            submitted_by=user,
            is_driver_feedback=is_from_driver,
            **validated_data
        )
        return feedback