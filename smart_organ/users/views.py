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

        tracking_list = OrganTracking.objects.filter(
        match__match_status="Proposed"
        ).select_related(
        "match",
        "match__donor",
        "match__receiver"
        )
        for tracking in tracking_list:
            tracking.css_class = get_status_class(tracking.status)

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



# ---------------------------------------------------
# Contact Hospital
# ---------------------------------------------------


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

    STATUS_ORDER = [s[0] for s in OrganTracking.STATUS_CHOICES]

    return render(request, "dashboard/track_organ.html", {
        "tracking": tracking,
        "status_order": STATUS_ORDER
    })

@login_required
def update_tracking(request, match_id):

    match = get_object_or_404(OrganMatch, id=match_id)
    tracking = get_object_or_404(OrganTracking, match=match)

    if request.user.role != "hospital":
        return redirect("dashboard")

    if request.method == "POST":

        tracking.status = request.POST.get("status")
        tracking.current_location = request.POST.get("current_location")
        tracking.save()

        Notification.objects.create(
            user=match.donor.donor.user,
            message=f"Transport status updated: {tracking.status}"
        )

        Notification.objects.create(
            user=match.receiver.receiver.user,
            message=f"Transport status updated: {tracking.status}"
        )

        return redirect("view_tracking", match_id=match.id)

    STATUS_LIST = [choice[0] for choice in OrganTracking.STATUS_CHOICES]

    return render(request, "dashboard/update_tracking.html", {
        "tracking": tracking,
        "statuses": STATUS_LIST
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


    return render(request, "dashboard/track_organ.html", {"tracking": tracking})
    from .models import OrganTracking
from django.shortcuts import render, redirect
from django.contrib import messages




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


    # ---------------------------------------------------
# Contact Hospital
# ---------------------------------------------------
from django.contrib import messages  # ensure messages is imported

@login_required
def contact_hospital(request, hospital_id):

    hospital = get_object_or_404(HospitalProfile, id=hospital_id)

    if request.method == "POST":
        message_text = request.POST.get("message")

        if message_text:
            ContactMessage.objects.create(
                sender=request.user,
                hospital=hospital,
                message=message_text
            )
            messages.success(request, "Message sent successfully!")
            return redirect("dashboard")
        else:
            messages.error(request, "Message cannot be empty!")

    return render(request, "dashboard/contact_hospital.html", {
        "hospital": hospital
    })


# ---------------------------------------------------
# Update Organ Status (Hospital Only)
# ---------------------------------------------------

@login_required
def update_organ_status(request):
    user = request.user
    if user.role != "hospital":
        messages.error(request, "You are not authorized to update organ status.")
        return redirect("dashboard")

    if request.method == "POST":
        tracking_id = request.POST.get("tracking_id")
        new_status = request.POST.get("status")

        try:
            organ_tracking = OrganTracking.objects.get(id=tracking_id)
            organ_tracking.status = new_status
            organ_tracking.save()
            messages.success(request, f"Organ status updated to '{new_status}' successfully!")
        except OrganTracking.DoesNotExist:
            messages.error(request, "Invalid Organ Tracking ID")

    organs = OrganTracking.objects.all().select_related("match", "match__donor", "match__receiver")

    return render(request, "users/update_organ_status.html", {"organs": organs})



def get_status_class(status):

    if status == "Transplant Completed":
        return "status-green"

    elif status == "In Transit":
        return "status-orange"

    elif status == "Picked Up":
        return "status-blue"

    elif status == "Ready for Transport":
        return "status-yellow"

    return "status-gray"
@login_required
def hospital_messages(request):

    if request.user.role != "hospital":
        return redirect("dashboard")

    hospital = HospitalProfile.objects.get(user=request.user)

    messages = ContactMessage.objects.filter(hospital=hospital).order_by("-sent_at")

    return render(request, "dashboard/hospital_messages.html", {
        "messages": messages
    })