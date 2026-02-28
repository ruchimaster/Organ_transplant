from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import UserSignUpForm, PersonProfileForm, HospitalProfileForm, OrganRequestForm, DonationRequestForm
from .models import PersonProfile, OrganRequest, DonationRequest
from django.contrib.auth.forms import AuthenticationForm

def signup(request):
    if request.method == 'POST':
        user_form = UserSignUpForm(request.POST)

        person_form = PersonProfileForm(request.POST, request.FILES)
        hospital_form = HospitalProfileForm(request.POST)

        


        if user_form.is_valid():
            print("User form errors:", user_form.errors)
            print("Person form errors:", person_form.errors)
            print("Hospital form errors:", hospital_form.errors)
            user = user_form.save()
            role = user_form.cleaned_data['role']

            if role in ['donor', 'receiver']:
                if person_form.is_valid():
                    profile = person_form.save(commit=False)
                    profile.user = user
                    profile.save()
                else:
                    return render(request, 'users/signup.html', {
                        'user_form': user_form,
                        'person_form': person_form,
                        'hospital_form': hospital_form
                    })
            else:  # hospital
                if hospital_form.is_valid():
                    profile = hospital_form.save(commit=False)
                    profile.user = user
                    profile.save()
                else:
                    return render(request, 'users/signup.html', {
                        'user_form': user_form,
                        'person_form': person_form,
                        'hospital_form': hospital_form
                    })

            login(request, user)
            return redirect('dashboard')

    else:
        user_form = UserSignUpForm()
        person_form = PersonProfileForm()
        hospital_form = HospitalProfileForm()

    return render(request, 'users/signup.html', {
        'user_form': user_form,
        'person_form': person_form,
        'hospital_form': hospital_form
    })

def dashboard(request):
    if request.user.role == 'donor':
        return render(request, 'dashboard/donor_dashboard.html', {
            'form': DonationRequestForm()
        })

    elif request.user.role == 'receiver':
        return render(request, 'dashboard/receiver_dashboard.html', {
            'form': OrganRequestForm()
        })

    else:
        return render(request, 'dashboard/hospital_dashboard.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {'form': form})
# Create your views here.
