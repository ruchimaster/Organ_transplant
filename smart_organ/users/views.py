from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .models import User
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
from .forms import (
    UserSignUpForm,
    PersonProfileForm,
    HospitalProfileForm,
    OrganRequestForm,
    DonationRequestForm
)


# ---------------------------------------------------
# Home View
# ---------------------------------------------------

def home(request):
    return render(request, "home.html")


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
        hospitals = HospitalProfile.objects.all()
        profile = PersonProfile.objects.get(user=user)

        if request.method == "POST":
            form = DonationRequestForm(request.POST, request.FILES)
            if form.is_valid():
                donation = form.save(commit=False)
                donation.donor = profile
                donation.save()
                return redirect("total_donor_requests")
        else:
            form = DonationRequestForm()

        donations = DonationRequest.objects.filter(donor=profile)

        return render(request, "dashboard/donor_dashboard.html", {
            "form": form,
            "donations": donations,
            "hospitals": hospitals
        })

    elif user.role == "receiver":
        profile = PersonProfile.objects.get(user=user)
        hospitals = HospitalProfile.objects.all()

        if request.method == "POST":
            form = OrganRequestForm(request.POST, request.FILES)
            if form.is_valid():
                req = form.save(commit=False)
                req.receiver = profile
                req.save()
                return redirect("total_receiver_requests")
        else:
            form = OrganRequestForm()

        requests = OrganRequest.objects.filter(receiver=profile)

        return render(request, "dashboard/receiver_dashboard.html", {
            "form": form,
            "requests": requests,
            "hospitals": hospitals
        })

    else:
        match_organs(request)

        hospital = HospitalProfile.objects.get(user=request.user)

        tracking_list = OrganTracking.objects.filter(
            match__match_status="Proposed"
        ).filter(
            Q(match__donor__license_number=hospital.license_number) |
            Q(match__receiver__license_number=hospital.license_number)
        ).select_related(
            "match",
            "match__donor",
            "match__receiver"
        ).order_by("-last_updated")

        for t in tracking_list:
            match = t.match
            t.show_track_button = False
            t.button_label = "Approve"
            t.button_disabled = False

            if match.donor.license_number == hospital.license_number:
                if match.donor_approved:
                    t.button_label = "Proposed"
                    t.button_disabled = True

            elif match.receiver.license_number == hospital.license_number:
                if match.receiver_approved:
                    t.button_label = "Proposed"
                    t.button_disabled = True

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

    urgent = OrganRequest.objects.filter(urgency_level="high")

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
# View Tracking
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


# ---------------------------------------------------
# Update Tracking
# ---------------------------------------------------

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

        if tracking.status == "Transplant Completed":
            match.match_status = "Completed"
            match.save()

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
    LOCATION_LIST = [
        "At Donor Hospital",
        "Ambulance - City Route",
        "Airport - Departure",
        "In Flight",
        "Airport - Arrival",
        "Ambulance - Receiver Route",
        "At Receiver Hospital"
    ]

    return render(request, "dashboard/update_tracking.html", {
        "tracking": tracking,
        "statuses": STATUS_LIST,
        "locations": LOCATION_LIST
    })


# ---------------------------------------------------
# Priority Calculation
# ---------------------------------------------------

def compute_priority(req, donor):

    score = 0

    urgency_weight = {
        "high": 100,
        "medium": 50,
        "low": 10
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
# Matching Engine
# ---------------------------------------------------

@login_required
def match_organs(request):

    donations = DonationRequest.objects.filter(status="Available")
    requests = list(OrganRequest.objects.filter(status="Pending"))

    for req in requests:

        best_candidate = None
        best_score = -1

        existing_match = OrganMatch.objects.filter(receiver=req).first()

        if existing_match and existing_match.match_status == "Approved":
            continue

        for donation in donations:

            donor_has_approved = OrganMatch.objects.filter(
                donor=donation,
                match_status="Approved"
            ).exists()

            if donor_has_approved:
                continue

            if donation.organ.lower() != req.organ_required.lower():
                continue

            if req.blood_group not in BLOOD_COMPATIBILITY.get(donation.blood_group, []):
                continue

            score = compute_priority(req, donation)

            if score > best_score:
                best_score = score
                best_candidate = donation

        if best_candidate:

            if existing_match:
                old_score = compute_priority(
                    existing_match.receiver,
                    existing_match.donor
                )

                if best_score > old_score:
                    existing_match.donor = best_candidate
                    existing_match.match_status = "Proposed"
                    existing_match.save()

                    Notification.objects.create(
                        user=req.receiver.user,
                        message="A better donor match has been found for you."
                    )

            else:
                match = OrganMatch.objects.create(
                    donor=best_candidate,
                    receiver=req,
                    match_status="Proposed"
                )

                OrganTracking.objects.get_or_create(match=match)

                Notification.objects.create(
                    user=best_candidate.donor.user,
                    message="A possible organ match has been proposed."
                )
                Notification.objects.create(
                    user=req.receiver.user,
                    message="A possible organ match was found and is awaiting hospital approval."
                )

    matches = list(OrganMatch.objects.select_related("donor", "receiver"))
    matches.sort(
        key=lambda m: compute_priority(m.receiver, m.donor),
        reverse=True
    )

    return render(request, "dashboard/match_results.html", {
        "matches": matches
    })


# ---------------------------------------------------
# Approve Match
# ---------------------------------------------------

@login_required
def approve_match(request, match_id):

    match = get_object_or_404(OrganMatch, id=match_id)
    hospital = HospitalProfile.objects.get(user=request.user)

    donation = match.donor
    receiver_req = match.receiver

    if hospital.license_number == donation.license_number:
        match.donor_approved = True

    if hospital.license_number == receiver_req.license_number:
        match.receiver_approved = True

    if match.donor_approved and match.receiver_approved:
        match.match_status = "Approved"
        donation.status = "Matched"
        receiver_req.status = "Matched"

        donation.save()
        receiver_req.save()

        Notification.objects.create(
            user=donation.donor.user,
            message=f"Great news! Your organ donation ({donation.organ}) has been approved by both hospitals. The transplant process will begin soon."
        )
        Notification.objects.create(
            user=receiver_req.receiver.user,
            message=f"Great news! Your organ request ({receiver_req.organ_required}) has been approved by both hospitals. The transplant process will begin soon."
        )

        OrganMatch.objects.filter(donor=donation).exclude(id=match.id).delete()
        OrganMatch.objects.filter(receiver=receiver_req).exclude(id=match.id).delete()

    match.save()

    return redirect("dashboard")


# ---------------------------------------------------
# Match History
# ---------------------------------------------------

@login_required
def match_history(request):

    if request.user.role != "hospital":
        return redirect("dashboard")

    hospital = HospitalProfile.objects.get(user=request.user)

    tracking_list = OrganTracking.objects.filter(
        match__match_status__in=["Approved", "Completed"]
    ).filter(
        Q(match__donor__license_number=hospital.license_number) |
        Q(match__receiver__license_number=hospital.license_number)
    ).select_related(
        "match",
        "match__donor",
        "match__receiver"
    ).order_by("-last_updated")

    return render(request, "dashboard/match_history.html", {
        "tracking_list": tracking_list
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

    LOCATION_LIST = [
        "At Donor Hospital",
        "Ambulance - City Route",
        "Airport - Departure",
        "In Flight",
        "Airport - Arrival",
        "Ambulance - Receiver Route",
        "At Receiver Hospital"
    ]

    STATUS_LIST = [choice[0] for choice in OrganTracking.STATUS_CHOICES]

    if request.method == "POST":
        tracking_id = request.POST.get("tracking_id")
        new_status = request.POST.get("status")
        new_location = request.POST.get("current_location")

        try:
            organ_tracking = OrganTracking.objects.get(id=tracking_id)
            organ_tracking.status = new_status
            organ_tracking.current_location = new_location
            organ_tracking.save()
            messages.success(request, "Tracking updated successfully!")

        except OrganTracking.DoesNotExist:
            messages.error(request, "Invalid Organ Tracking ID")

    active_organs = OrganTracking.objects.exclude(status="Transplant Completed")
    completed_organs = OrganTracking.objects.filter(status="Transplant Completed")

    return render(request, "users/update_organ_status.html", {
        "organs": active_organs,
        "active_organs": active_organs,
        "completed_organs": completed_organs,
        "statuses": STATUS_LIST,
        "locations": LOCATION_LIST
    })


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


# ---------------------------------------------------
# Total Requests
# ---------------------------------------------------

@login_required
def total_receiver_requests(request):

    profile = PersonProfile.objects.get(user=request.user)
    requests = OrganRequest.objects.filter(receiver=profile)

    return render(request, "dashboard/Total_Receiver_Request.html", {
        "requests": requests
    })


@login_required
def total_donor_requests(request):

    profile = PersonProfile.objects.get(user=request.user)
    donations = DonationRequest.objects.filter(donor=profile)

    return render(request, "dashboard/Total_Donor_Request.html", {
        "donations": donations
    })


# ---------------------------------------------------
# Tracking List
# ---------------------------------------------------

@login_required
def tracking_list(request):

    user = request.user

    if user.role == "receiver":
        profile = PersonProfile.objects.get(user=user)
        tracking_list = OrganTracking.objects.filter(
            match__receiver__receiver=profile
        ).select_related("match", "match__donor", "match__receiver")

    elif user.role == "hospital":
        tracking_list = OrganTracking.objects.all().select_related(
            "match", "match__donor", "match__receiver"
        )

    else:
        tracking_list = None

    return render(request, "dashboard/tracking_list.html", {
        "tracking_list": tracking_list
    })


# ---------------------------------------------------
# Chat View
# ---------------------------------------------------

@login_required
def chat_view(request, hospital_id, user_id=None):

    hospital = get_object_or_404(HospitalProfile, id=hospital_id)
    current_user = request.user

    if current_user.role == "hospital":
        if user_id:
            thread_user = get_object_or_404(User, id=user_id)
        else:
            return redirect("hospital_inbox")

        chats = ContactMessage.objects.filter(
            hospital=hospital
        ).filter(
            Q(sender=thread_user) | Q(receiver=thread_user)
        ).order_by("sent_at")

    else:
        chats = ContactMessage.objects.filter(
            hospital=hospital
        ).filter(
            Q(sender=current_user) | Q(receiver=current_user)
        ).order_by("sent_at")

    if request.method == "POST":
        message_text = request.POST.get("message")

        if message_text:
            if current_user.role == "hospital":
                receiver = thread_user
            else:
                receiver = hospital.user

            ContactMessage.objects.create(
                sender=current_user,
                receiver=receiver,
                hospital=hospital,
                message=message_text
            )

            Notification.objects.create(
                user=receiver,
                message=f"New message from {current_user.username}"
            )

            if current_user.role == "hospital":
                return redirect("chat_view_with_user", hospital_id=hospital.id, user_id=thread_user.id)
            else:
                return redirect("chat_view", hospital_id=hospital.id)

    return render(request, "dashboard/chat.html", {
        "chats": chats,
        "hospital": hospital
    })


# ---------------------------------------------------
# Hospital Inbox
# ---------------------------------------------------

@login_required
def hospital_inbox(request):

    if request.user.role != "hospital":
        return redirect("dashboard")

    hospital = HospitalProfile.objects.get(user=request.user)

    conversations = ContactMessage.objects.filter(
        hospital=hospital
    ).values("sender").distinct()

    users = User.objects.filter(id__in=[c["sender"] for c in conversations])

    return render(request, "dashboard/hospital_inbox.html", {
        "users": users,
        "hospital": hospital
    })