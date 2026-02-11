from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import UserSignUpForm, PersonProfileForm, HospitalProfileForm

def signup(request):
    if request.method == 'POST':
        user_form = UserSignUpForm(request.POST)

        person_form = PersonProfileForm(request.POST, request.FILES)
        hospital_form = HospitalProfileForm(request.POST)

        if user_form.is_valid():
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
    if request.user.role in ['donor', 'receiver']:
        return render(request, 'dashboard/person_dashboard.html')
    else:
        return render(request, 'dashboard/hospital_dashboard.html')


