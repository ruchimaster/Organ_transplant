from django.shortcuts import render, redirect, get_object_or_404
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
    DonationRequest,
    OrganRequest,
    OrganMatch,
    OrganTracking,
    Notification,
    ContactMessage
)

# ---------------------------------------------------
# Signup View
# ---------------------------------------------------

def signup(request):

    user_form = UserSignUpForm(request.POST or None)
    person_form = PersonProfileForm(request.POST or None, request.FILES or None)
    hospital_form = HospitalProfileForm(request.POST or None)

    if request.method == "POST":

        if user_form.is_valid():

            user = user_form.save()
            role = user_form.cleaned_data["role"]

            if role in ["donor", "receiver"]:

                if person_form.is_valid():
                    profile = person_form.save(commit=False)
                    profile.user = user
                    profile.save()

            else:

                if hospital_form.is_valid():
                    profile = hospital_form.save(commit=False)
                    profile.user = user
                    profile.save()

            login(request, user)
            return redirect("dashboard")

    return render(request, "users/signup.html", {
        "user_form": user_form,
        "person_form": person_form,
        "hospital_form": hospital_form
    })


# ---------------------------------------------------
# Login View
# ---------------------------------------------------

def login_view(request):

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST":

        if form.is_valid():

            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(username=username, password=password)

            if user:
                login(request, user)
                return redirect("dashboard")

    return render(request, "users/login.html", {"form": form})


# ---------------------------------------------------
# Dashboard View
# ---------------------------------------------------

@login_required
def dashboard(request):

    user = request.user

    if user.role == "donor":

        profile = PersonProfile.objects.get(user=user)

        if request.method == "POST":
            form = DonationRequestForm(request.POST, request.FILES)

            if form.is_valid():
                donation = form.save(commit=False)
                donation.donor = profile
                donation.save()

        else:
            form = DonationRequestForm()

        donations = DonationRequest.objects.filter(donor=profile)

        return render(request, "dashboard/donor_dashboard.html", {
            "form": form,
            "donations": donations
        })


    elif user.role == "receiver":

        profile = PersonProfile.objects.get(user=user)

        if request.method == "POST":
            form = OrganRequestForm(request.POST, request.FILES)

            if form.is_valid():
                req = form.save(commit=False)
                req.receiver = profile
                req.save()

        else:
            form = OrganRequestForm()

        requests = OrganRequest.objects.filter(receiver=profile)

        return render(request, "dashboard/receiver_dashboard.html", {
            "form": form,
            "requests": requests
        })


    else:

        hospital = HospitalProfile.objects.get(user=user)

        tracking_list = OrganTracking.objects.filter(
            match__match_status="Proposed"
        ).select_related("match", "match__donor", "match__receiver")

        return render(request, "dashboard/hospital_dashboard.html", {
            "tracking_list": tracking_list
        })


# ---------------------------------------------------
# Notifications View
# ---------------------------------------------------

@login_required
def notifications_view(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    notifications.filter(is_read=False).update(is_read=True)

    return render(request, "users/notifications.html", {
        "notifications": notifications
    })


# ---------------------------------------------------
# Urgent Requests
# ---------------------------------------------------

def urgent_requests(request):

    urgent = OrganRequest.objects.filter(
        urgency_level="high"
    )

    return render(request, "dashboard/urgent_requests.html", {
        "urgent": urgent
    })


# ---------------------------------------------------
# Tracking View
# ---------------------------------------------------



# ---------------------------------------------------
# Update Status
# ---------------------------------------------------


@login_required
def update_status(request, donation_id):


    donation = get_object_or_404(DonationRequest, id=donation_id)


    if request.method == "POST":
        donation.status = request.POST.get("status")
        donation.save()


    return redirect("dashboard")

@login_required
def view_tracking(request, match_id):

    tracking = OrganTracking.objects.filter(
        match__id=match_id
    ).select_related("match").first()

    if not tracking:
        return render(request, "dashboard/track_organ.html", {
            "tracking": None,
            "error": "Tracking not found."
        })

    user = request.user

    allowed = (
        user == tracking.match.donor.donor.user or
        user == tracking.match.receiver.receiver.user or
        user.role == "hospital"
    )

    if not allowed:
        return redirect("dashboard")

    return render(request, "dashboard/track_organ.html", {
        "tracking": tracking
    })


# ---------------------------------------------------
# Priority Calculation
# ---------------------------------------------------

def compute_priority(req, donor):

    score = 0

    urgency_weight = {
        "high": 10,
        "medium": 5,
        "low": 1
    }

    score += urgency_weight.get(req.urgency_level, 0)

    if donor.organ.lower() == req.organ_required.lower():
        score += 1

    if donor.blood_group == req.blood_group:
        score += 0.5

    return score


# ---------------------------------------------------
# Blood Compatibility Map
# ---------------------------------------------------

BLOOD_COMPATIBILITY = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}


# ---------------------------------------------------
# Matching Engine (FINAL VERSION)
# ---------------------------------------------------

@login_required
def match_organs(request):

    donations = DonationRequest.objects.filter(status="Available")
    requests = list(OrganRequest.objects.filter(status="Pending"))

    for donation in donations:

        donor_count = OrganMatch.objects.filter(
            donor=donation,
            match_status="Proposed"
        ).count()

        if donor_count >= 3:
            continue

        OrganMatch.objects.filter(
            donor=donation,
            match_status="Proposed"
        ).update(match_status="Rejected")

        candidates = []

        for req in requests:

            receiver_count = OrganMatch.objects.filter(
                receiver=req,
                match_status="Proposed"
            ).count()

            if receiver_count >= 3:
                continue

            if donation.organ.lower() != req.organ_required.lower():
                continue

            if req.blood_group not in BLOOD_COMPATIBILITY.get(donation.blood_group, []):
                continue

            score = compute_priority(req, donation)

            candidates.append((score, donation, req))

        if candidates:

            candidates.sort(reverse=True, key=lambda x: x[0])

            _, best_donation, best_req = candidates[0]

            match, created = OrganMatch.objects.get_or_create(
                donor=best_donation,
                receiver=best_req
            )

            if created:

                match.match_status = "Proposed"
                match.save()

                OrganTracking.objects.get_or_create(match=match)

                Notification.objects.create(
                    user=best_donation.donor.user,
                    message="A possible organ match has been proposed."
                )

                Notification.objects.create(
                    user=best_req.receiver.user,
                    message="A possible organ match was found and is awaiting hospital approval."
                )

    matches = OrganMatch.objects.select_related(
        "donor", "receiver"
    ).order_by("-id")

    return render(request, "dashboard/match_results.html", {
        "matches": matches
    })


# ---------------------------------------------------
# Approve Match
# ---------------------------------------------------

@login_required
def approve_match(request, match_id):

    match = get_object_or_404(OrganMatch, id=match_id)

    donation = match.donor
    receiver_req = match.receiver

    match.match_status = "Approved"
    match.save()

    donation.status = "Matched"
    receiver_req.status = "Matched"

    donation.save()
    receiver_req.save()

    Notification.objects.create(
        user=receiver_req.receiver.user,
        message="Your organ match has been approved by hospital."
    )

    return redirect("dashboard")


# ---------------------------------------------------
# Match History
# ---------------------------------------------------

@login_required
def match_history(request):

    if request.user.role != "hospital":
        return redirect("dashboard")

    tracking_list = OrganTracking.objects.filter(
        match__match_status="Approved"
    ).select_related(
        "match",
        "match__donor",
        "match__receiver"
    ).order_by("-last_updated")

    return render(request, "dashboard/match_history.html", {
        "tracking_list": tracking_list
    })