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
       return f"{self.user.username} ({self.role})"


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
   organ_required = models.CharField(max_length=100, null=True, blank=True)
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



class OrganMatch(models.Model):
    donor = models.ForeignKey(DonationRequest, on_delete=models.CASCADE)
    receiver = models.ForeignKey(OrganRequest, on_delete=models.CASCADE)
    match_status = models.CharField(max_length=50, default="Matched")

    def __str__(self):
        return f"Match {self.id}"


class OrganTracking(models.Model):
    match = models.OneToOneField(OrganMatch, on_delete=models.CASCADE)
    current_location = models.CharField(max_length=255, default="At Donor Hospital")
    status = models.CharField(max_length=50, default="Ready for Transport")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tracking for {self.match.id}: {self.status}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.message


class ContactMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    hospital = models.ForeignKey(HospitalProfile, on_delete=models.CASCADE)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username} → {self.hospital.hospital_name}"