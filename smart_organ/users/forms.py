from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, PersonProfile, HospitalProfile,OrganRequest, DonationRequest

class UserSignUpForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password1', 'password2']


class PersonProfileForm(forms.ModelForm):
    class Meta:
        model = PersonProfile
        exclude = ['user']


class HospitalProfileForm(forms.ModelForm):
    class Meta:
        model = HospitalProfile
        exclude = ['user']



class OrganRequestForm(forms.ModelForm):
   class Meta:
       model = OrganRequest
       exclude = ['receiver', 'status']




class DonationRequestForm(forms.ModelForm):
   class Meta:
       model = DonationRequest
       exclude = ['donor', 'status']