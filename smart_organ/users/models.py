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