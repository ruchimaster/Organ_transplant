from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    ROLE_CHOICES = [
        ('donor', 'Donor'),
        ('receiver', 'Receiver'),
        ('hospital', 'Hospital')
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    # Person profile (donor/receiver)
class PersonProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    organ = models.CharField(max_length=50, null=True, blank=True)
    medical_report = models.FileField(upload_to='medical_reports/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.organ})"

class HospitalProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hospital_name = models.CharField(max_length=100)
    address = models.TextField()
    license_number = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)

    def __str__(self):
        return self.hospital_name

class ContactMessage(models.Model):
    hospital = models.ForeignKey(HospitalProfile, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message to {self.HospitalProfile.name}"

  
from django.conf import settings


class Notification(models.Model):
    ORGAN_MATCH_FOUND = "organ_match_found"
    URGENT_ORGAN_REQUEST = "urgent_organ_request"
    DONATION_REQUEST_ACCEPTED = "donation_request_accepted"

    NOTIFICATION_TYPE_CHOICES = [
        (ORGAN_MATCH_FOUND, "Organ Match Found"),
        (URGENT_ORGAN_REQUEST, "Urgent Organ Request"),
        (DONATION_REQUEST_ACCEPTED, "Donation Request Accepted"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        default=ORGAN_MATCH_FOUND,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"[{status}] {self.get_notification_type_display()} → {self.user}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=["is_read"])