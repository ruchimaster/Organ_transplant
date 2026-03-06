from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm

from .forms import (
    UserSignUpForm,
    PersonProfileForm,
    HospitalProfileForm,
    OrganRequestForm,
    DonationRequestForm
)

from .models import (
    PersonProfile,
    HospitalProfile,
    OrganRequest,
    DonationRequest,
    OrganMatch,
    OrganTracking,
    ContactMessage,
    Notification
)


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

    else:  # hospital
        hospital = HospitalProfile.objects.get(user=request.user)

        tracking_list = OrganTracking.objects.filter(
            match__donor__donor__hospital=hospital
        ).select_related(
            'match',
            'match__donor',
            'match__donor__donor',
            'match__receiver',
            'match__receiver__receiver'
        )

        return render(request, 'dashboard/hospital_dashboard.html', {
            'tracking_list': tracking_list
        })


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


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)

    notifications.filter(is_read=False).update(is_read=True)

    context = {
        "notifications": notifications
    }

    return render(request, "users/notifications.html", context)


@login_required
def match_organs(request):
    donations = DonationRequest.objects.filter(status="Available")
    requests = OrganRequest.objects.filter(status="Pending").order_by('-urgency_level')

    for donation in donations:
        for req in requests:
            if donation.organ.lower() == req.organ_required.lower() and donation.blood_group == req.blood_group:

                match, created = OrganMatch.objects.get_or_create(
                    donor=donation,
                    receiver=req
                )

                if created:
                    OrganTracking.objects.create(match=match)

                donation.status = "Matched"
                req.status = "Matched"
                donation.save()
                req.save()

                Notification.objects.create(
                    user=donation.donor.user,
                    message=f"Your organ has been matched with {req.receiver.user.username}"
                )

                Notification.objects.create(
                    user=req.receiver.user,
                    message=f"You have been matched with donor {donation.donor.user.username}"
                )

    matches = OrganMatch.objects.all().select_related(
        "donor__donor__user",
        "receiver__receiver__user"
    )

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