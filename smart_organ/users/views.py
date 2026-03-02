from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import UserSignUpForm, PersonProfileForm, HospitalProfileForm, OrganRequestForm, DonationRequestForm
from .models import OrganRequest, DonationRequest

from django.contrib.auth.decorators import login_required
from .models import PersonProfile,Notification,ContactMessage,HospitalProfile


from django.contrib.auth.forms import AuthenticationForm
from .models import OrganMatch, OrganTracking

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

@login_required
def dashboard(request):

    if request.user.role == 'donor':
        profile = PersonProfile.objects.get(user=request.user)

        if request.method == 'POST':
            form = DonationRequestForm(request.POST, request.FILES)
            if form.is_valid():
                donation = form.save(commit=False)
                donation.donor = profile
                donation.save()
        else:
            form = DonationRequestForm()

        donations = DonationRequest.objects.filter(donor=profile)

        return render(request, 'dashboard/donor_dashboard.html', {
            'form': form,
            'donations': donations
        })

    elif request.user.role == 'receiver':
        profile = PersonProfile.objects.get(user=request.user)

        if request.method == 'POST':
            form = OrganRequestForm(request.POST, request.FILES)
            if form.is_valid():
                req = form.save(commit=False)
                req.receiver = profile
                req.save()
        else:
            form = OrganRequestForm()

        requests = OrganRequest.objects.filter(receiver=profile)

        return render(request, 'dashboard/receiver_dashboard.html', {
            'form': form,
            'requests': requests
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
# views.py

@login_required
def match_organs(request):
    donations = DonationRequest.objects.filter(status="Available")
    requests = OrganRequest.objects.filter(status="Pending").order_by('-urgency_level')

    matches_created = []

    for donation in donations:
        for req in requests:
            if donation.organ.lower() == req.organ_required.lower() and donation.blood_group == req.blood_group:
                # create match only if it does not exist
                match, created = OrganMatch.objects.get_or_create(
                    donor=donation,
                    receiver=req
                )
                if created:
                    # create tracking automatically
                    OrganTracking.objects.create(match=match)

                donation.status = "Matched"
                req.status = "Matched"
                donation.save()
                req.save()

                # Notifications
                Notification.objects.create(
                    user=donation.donor.user,
                    message=f"Your organ has been matched with {req.receiver.user.username}"
                )
                Notification.objects.create(
                    user=req.receiver.user,
                    message=f"You have been matched with donor {donation.donor.user.username}"
                )

                matches_created.append(match)

    matches = OrganMatch.objects.all().select_related("donor__donor__user", "receiver__receiver__user")
    return render(request, "dashboard/match_results.html", {"matches": matches})

def urgent_requests(request):
    urgent = OrganRequest.objects.filter(urgency_level="high")
    return render(request, "dashboard/urgent_requests.html", {"urgent": urgent})


@login_required
def update_status(request, donation_id):
    donation = DonationRequest.objects.get(id=donation_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        donation.status = new_status
        donation.save()

    return redirect("dashboard")


@login_required
def contact_hospital(request, hospital_id):
    hospital = HospitalProfile.objects.get(id=hospital_id)

    if request.method == "POST":
        message = request.POST.get("message")

        ContactMessage.objects.create(
            sender=request.user,
            hospital=hospital,
            message=message
        )

        return redirect("dashboard")

    return render(request, "dashboard/contact_hospital.html", {"hospital": hospital})


@login_required
def notifications(request):
    notes = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "dashboard/notifications.html", {"notes": notes})
# views.py

@login_required
def view_tracking(request, match_id):
    tracking = OrganTracking.objects.filter(match__id=match_id).first()

    if not tracking:
        return render(request, "dashboard/track_organ.html", {
            "tracking": None,
            "error": "Tracking not found for this match."
        })

    user = request.user
    allowed = (
        user == tracking.match.donor.donor.user or
        user == tracking.match.receiver.receiver.user or
        user.role == "hospital"
    )

    if not allowed:
        return redirect("dashboard")

    return render(request, "dashboard/track_organ.html", {"tracking": tracking})




# @login_required
# def update_tracking(request, match_id):
#     if request.user.role != "hospital":
#         return redirect("dashboard")

#     tracking = OrganTracking.objects.filter(match__id=match_id).first()
#     if not tracking:
#         return redirect("dashboard")

#     if request.method == "POST":
#         tracking.current_location = request.POST.get("location")
#         tracking.status = request.POST.get("status")
#         tracking.save()
#         return redirect("view_tracking", match_id=match_id)

#     return render(request, "dashboard/update_tracking.html", {"tracking": tracking})