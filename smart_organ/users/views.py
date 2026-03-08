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

        # FIX: show only proposed matches waiting for approval
        tracking_list = OrganTracking.objects.filter(
            match__match_status="Proposed"
        ).select_related("match", "match__donor", "match__receiver")

        return render(request, "dashboard/hospital_dashboard.html", {
            "tracking_list": tracking_list
        })


# ---------------------------------------------------
# Notifications
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
# Update Status
# ---------------------------------------------------

@login_required
def update_status(request, donation_id):

    donation = get_object_or_404(DonationRequest, id=donation_id)

    if request.method == "POST":
        donation.status = request.POST.get("status")
        donation.save()

    return redirect("dashboard")


# ---------------------------------------------------
# Contact Hospital
# ---------------------------------------------------

@login_required
def contact_hospital(request, hospital_id):

    hospital = get_object_or_404(HospitalProfile, id=hospital_id)

    if request.method == "POST":
        message = request.POST.get("message")

        ContactMessage.objects.create(
            sender=request.user,
            hospital=hospital,
            message=message
        )

        messages.success(request, "Message sent successfully!")
        return redirect("dashboard")

    return render(request, "users/contact_hospital.html", {"hospital": hospital})
# ---------------------------------------------------
# Tracking View
# ---------------------------------------------------

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
# Priority Matching Engine
# ---------------------------------------------------

def compute_priority(req, donor):

    score = 0

    if req.urgency_level == "high":
        score += 3
    elif req.urgency_level == "medium":
        score += 2
    else:
        score += 1

    if donor.blood_group == req.blood_group:
        score += 2

    if donor.organ.lower() == req.organ_required.lower():
        score += 1

    return score


# ---------------------------------------------------
# Organ Matching Engine
# ---------------------------------------------------

@login_required
def match_organs(request):

    donations = DonationRequest.objects.filter(status="Available")
    requests = list(OrganRequest.objects.filter(status="Pending"))

    priority_map = {
        "high": 3,
        "medium": 2,
        "low": 1
    }

    requests.sort(key=lambda r: priority_map.get(r.urgency_level, 0), reverse=True)

    for donation in donations:

        # FIX: prevent donor from matching multiple receivers
        # Allow re-matching if match is only Proposed
        existing_match = OrganMatch.objects.filter(donor=donation).first()

        if existing_match:

    # If hospital already approved → do not change
            if existing_match.match_status == "Approved":
                continue

    # If only proposed → delete and recompute
            existing_match.delete()

        candidates = []

        for req in requests:

            if donation.organ.lower() == req.organ_required.lower():

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

                OrganTracking.objects.create(match=match)

                Notification.objects.create(
                    user=best_donation.donor.user,
                    message="A possible organ match has been proposed."
                )

                Notification.objects.create(
                    user=best_req.receiver.user,
                    message="A possible organ match was found and is awaiting hospital approval."
                )

    # FIX: optimized query
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

    # FIX: correct receiver filtering
    receivers = OrganRequest.objects.filter(
        organ_required=donation.organ,
        status="Pending"
    )

    best_receiver = None
    best_score = -1

    for req in receivers:

        score = compute_priority(req, donation)

        if score > best_score:
            best_score = score
            best_receiver = req

    if best_receiver:

        match.receiver = best_receiver
        match.match_status = "Approved"
        match.save()

        donation.status = "Matched"
        best_receiver.status = "Matched"

        donation.save()
        best_receiver.save()

        Notification.objects.create(
            user=best_receiver.receiver.user,
            message="Your organ match has been approved by the hospital."
        )

    return redirect("dashboard")

    return render(request, "dashboard/track_organ.html", {"tracking": tracking})
    from .models import OrganTracking
from django.shortcuts import render, redirect
from django.contrib import messages


def update_organ_status(request):
    if request.method == "POST":
        tracking_id = request.POST.get("tracking_id")
        new_status = request.POST.get("status")

        try:
            organ = OrganTracking.objects.get(id=tracking_id)
            organ.status = new_status
            organ.save()

            messages.success(request, "Organ status updated successfully!")

        except OrganTracking.DoesNotExist:
            messages.error(request, "Invalid Organ ID")

    organs = OrganTracking.objects.all()

    return render(request, "users/update_organ_status.html", {"organs": organs})

