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
    
# Organ request (for receivers)
class OrganRequest(models.Model):
    receiver = models.ForeignKey(PersonProfile, on_delete=models.CASCADE)
    organ_required = models.CharField(max_length=50)
    blood_group = models.CharField(max_length=5)
    urgency_level = models.CharField(max_length=20, choices=[('low','Low'),('medium','Medium'),('high','High')])
    medical_report = models.FileField(upload_to='organ_requests/')
    status = models.CharField(max_length=20, default='Pending')  # Pending, Matched, Transplanted

    def __str__(self):
        return f"{self.receiver.user.username} - {self.organ_required}"


# Organ donation (for donors)
class DonationRequest(models.Model):
    donor = models.ForeignKey(PersonProfile, on_delete=models.CASCADE)
    organ = models.CharField(max_length=50)
    blood_group = models.CharField(max_length=5)
    medical_report = models.FileField(upload_to='donation_requests/')
    status = models.CharField(max_length=20, default='Available')  # Available, Matched, Transplanted

    def __str__(self):
        return f"{self.donor.user.username} - {self.organ}"

