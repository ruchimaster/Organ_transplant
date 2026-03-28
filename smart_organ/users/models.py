from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
# Create your models here.


class User(AbstractUser):
   ROLE_CHOICES = [
       ('donor', 'Donor'),
       ('receiver', 'Receiver'),
       ('hospital', 'Hospital')
   ]
   role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="receiver")

   def __str__(self):
       return f"{self.username} ({self.role})"
  
   # Person profile (donor/receiver)
class PersonProfile(models.Model):
   user = models.OneToOneField(User, on_delete=models.CASCADE)
   age = models.IntegerField(null=True, blank=True,validators=[
        MinValueValidator(1),
        MaxValueValidator(99),
    ])
   gender = models.CharField(max_length=10, null=True, blank=True, choices=[('Male','Male'),('Female','Female')])
   contact_number = models.CharField(max_length=15, null=True, blank=True)
   blood_group = models.CharField(max_length=5, null=True, blank=True, choices=[('A+', 'A+'),
    ('A-', 'A-'),
    ('B+', 'B+'),
    ('B-', 'B-'),
    ('AB+', 'AB+'),
    ('AB-', 'AB-'),
    ('O+', 'O+'),
    ('O-', 'O-')])
   medical_report = models.FileField(upload_to='medical_reports/', null=True, blank=True)


   def __str__(self):
       return f"{self.user.username} ({self.user.role})"


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
   organ_required = models.CharField(max_length=100, null=True, blank=True, choices=[('Heart', 'Heart'),
    ('Lung', 'Lung'),
    ('Liver', 'Liver'),
    ('Kidney', 'Kidney'),
    ('Pancreas', 'Pancreas'),
    ('Intestine', 'Intestine'),
    ('Cornea', 'Cornea'),
    ('Bone Marrow', 'Bone Marrow'),
    ('Skin', 'Skin'),
    ('Bone', 'Bone'),
    ('Heart Valve', 'Heart Valve')])
   blood_group = models.CharField(max_length=5,choices=[('A+', 'A+'),
    ('A-', 'A-'),
    ('B+', 'B+'),
    ('B-', 'B-'),
    ('AB+', 'AB+'),
    ('AB-', 'AB-'),
    ('O+', 'O+'),
    ('O-', 'O-')])
   urgency_level = models.CharField(max_length=20, choices=[('low','Low'),('medium','Medium'),('high','High')])
   address = models.TextField(default="Unknown")
   license_number = models.CharField(max_length=50,default=0)
   medical_report = models.FileField(upload_to='organ_requests/')
   status = models.CharField(max_length=20, default='Pending')  # Pending, Matched, Transplanted
   
   def __str__(self):
       return f"{self.receiver.user.username} - {self.organ_required}"




# Organ donation (for donors)
class DonationRequest(models.Model):
   donor = models.ForeignKey(PersonProfile, on_delete=models.CASCADE)
   organ = models.CharField(max_length=50,choices=[('Heart', 'Heart'),
    ('Lung', 'Lung'),
    ('Liver', 'Liver'),
    ('Kidney', 'Kidney'),
    ('Pancreas', 'Pancreas'),
    ('Intestine', 'Intestine'),
    ('Cornea', 'Cornea'),
    ('Bone Marrow', 'Bone Marrow'),
    ('Skin', 'Skin'),
    ('Bone', 'Bone'),
    ('Heart Valve', 'Heart Valve')])
   blood_group = models.CharField(max_length=5,choices=[('A+', 'A+'),
    ('A-', 'A-'),
    ('B+', 'B+'),
    ('B-', 'B-'),
    ('AB+', 'AB+'),
    ('AB-', 'AB-'),
    ('O+', 'O+'),
    ('O-', 'O-')])
   address = models.TextField(default="Unknown")
   license_number = models.CharField(max_length=50,default = 0)
   medical_report = models.FileField(upload_to='donation_requests/')
   status = models.CharField(max_length=20, default='Available')  # Available, Matched, Transplanted


   def __str__(self):
       return f"{self.donor.user.username} - {self.organ}"



class OrganMatch(models.Model):
    donor = models.ForeignKey(DonationRequest, on_delete=models.CASCADE)
    receiver = models.ForeignKey(OrganRequest, on_delete=models.CASCADE)
    match_status = models.CharField(max_length=50, default="Proposed")
    donor_approved = models.BooleanField(default=False)
    receiver_approved = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.donor.donor.user.username} → {self.receiver.receiver.user.username} ({self.receiver.organ_required})"
# class ContactMessage(models.Model):
#     hospital = models.ForeignKey(HospitalProfile, on_delete=models.CASCADE)
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     message = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Message to {self.HospitalProfile.name}"


# class Notification(models.Model):
#     ORGAN_MATCH_FOUND = "organ_match_found"
#     URGENT_ORGAN_REQUEST = "urgent_organ_request"
#     DONATION_REQUEST_ACCEPTED = "donation_request_accepted"

#     NOTIFICATION_TYPE_CHOICES = [
#         (ORGAN_MATCH_FOUND, "Organ Match Found"),
#         (URGENT_ORGAN_REQUEST, "Urgent Organ Request"),
#         (DONATION_REQUEST_ACCEPTED, "Donation Request Accepted"),
#     ]

#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="notifications",
#     )
#     notification_type = models.CharField(
#         max_length=50,
#         choices=NOTIFICATION_TYPE_CHOICES,
#         default=ORGAN_MATCH_FOUND,
#     )

    
class OrganTracking(models.Model):

    STATUS_CHOICES = [
        ("Ready for Transport", "Ready for Transport"),
        ("Picked Up", "Picked Up"),
        ("In Transit", "In Transit"),
        ("Arrived at Receiver Hospital", "Arrived at Receiver Hospital"),
        ("Handed Over to Surgery Team", "Handed Over to Surgery Team"),
        ("Transplant Completed", "Transplant Completed")
    ]

    match = models.OneToOneField(
        "OrganMatch",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    current_location = models.CharField(max_length=255, default="At Donor Hospital")

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="Ready for Transport"
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tracking Match {self.match.id}"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.message}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=["is_read"])

class ContactMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    hospital = models.ForeignKey(HospitalProfile, on_delete=models.CASCADE)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username} → {self.hospital.hospital_name}"

