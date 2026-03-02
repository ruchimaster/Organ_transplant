from django.contrib import admin
from .models import (
    User,
    PersonProfile,
    HospitalProfile,
    DonationRequest,
    OrganRequest,
    OrganMatch,
    OrganTracking
)

admin.site.register(User)
admin.site.register(PersonProfile)
admin.site.register(HospitalProfile)
admin.site.register(DonationRequest)
admin.site.register(OrganRequest)
admin.site.register(OrganMatch)
admin.site.register(OrganTracking)