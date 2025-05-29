from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
import requests
from django.http import JsonResponse
from .models import SubscriptionPlan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer
from .permissions import HasActiveSubscription
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import SubscriptionPlan, Subscription
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.views import LogoutView

# stripe requirement 
# import stripe
from django.conf import settings
from django.urls import reverse

import razorpay
razor = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID,
                              settings.RAZORPAY_KEY_SECRET))

# -------- create order --------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def razorpay_create_order(request):
    plan_id = request.data["plan_id"]
    plan    = SubscriptionPlan.objects.get(id=plan_id)

    order = razor.order.create({
        "amount": plan.price * 100,      # 1 rupee -> 100 paise
        "currency": "INR",
        "payment_capture": 1,            # auto-capture
        "notes": {
            "user_id": request.user.id,
            "plan_id": plan.id,
        }
    })
    return Response({"order": order})

# -------- verify signature --------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def razorpay_verify(request):
    """
    Body is  {
      razorpay_payment_id, razorpay_order_id, razorpay_signature
    }
    """
    try:
        razor.utility.verify_payment_signature(request.data)
    except razorpay.errors.SignatureVerificationError:
        return Response({"detail": "Signature mismatch"}, status=400)

    order = razor.order.fetch(request.data["razorpay_order_id"])
    user_id = int(order["notes"]["user_id"])
    plan_id = int(order["notes"]["plan_id"])

    Subscription.objects.filter(user_id=user_id).delete()
    Subscription.create(User.objects.get(id=user_id),
                        SubscriptionPlan.objects.get(id=plan_id))
    return Response({"status": "activated"})

# -------- thank-you page --------
@login_required
def thank_you(request):
    return render(request, "subscriptions/thank_you.html")


class LogoutViewAllowGet(LogoutView):
 
    http_method_names = ["get", "post", "head", "options"]

def signup_view(request):

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()                               
            messages.success(request, "Account created! You can now log in.")
            return redirect("login")                  
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form})

def plans_page(request):
    plans = SubscriptionPlan.objects.all()
    return render(request, "subscriptions/plans.html", {"plans": plans})

@login_required
def me_page(request):
    sub = getattr(request.user, "subscription", None)
    return render(request, "subscriptions/me.html", {"sub": sub})

@login_required
@require_POST
def subscribe_html(request):
    plan_id = request.POST.get("plan_id")
    # reuse existing helper
    Subscription.objects.filter(user=request.user).delete()
    plan = SubscriptionPlan.objects.get(id=plan_id)
    Subscription.create(request.user, plan)
    return redirect("me")

@login_required
@require_POST
def cancel_html(request):
    sub = getattr(request.user, "subscription", None)
    if sub:
        sub.active = False
        sub.end = timezone.now()
        sub.save()
    return redirect("me")

@login_required
def premium_demo(request):
    """
    Calls the JSON endpoint from the browser so the user sees the raw result.
    """

    # Build absolute URL to the API
    api_url = request.build_absolute_uri("/api/premium/")
    # Forward session cookie so DRF sees the same login
    cookies = {"sessionid": request.COOKIES.get("sessionid")}
    r = requests.get(api_url, cookies=cookies)
    return JsonResponse({"status": r.status_code, "json": r.json()})

##  Stripe logic

# stripe.api_key = settings.STRIPE_SECRET_KEY

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def create_checkout_session(request):
#     """
#     Called by JS → returns checkout_url for Stripe hosted page.
#     """
#     plan_id = request.data["plan_id"]
#     plan = SubscriptionPlan.objects.get(id=plan_id)

#     session = stripe.checkout.Session.create(
#         mode="payment",
#         payment_method_types=["card"],
#         line_items=[{
#             "price_data": {
#                 "currency": "inr",
#                 "unit_amount": plan.price * 100,      # rupees → paise
#                 "product_data": {"name": f"{plan.name} plan"},
#             },
#             "quantity": 1,
#         }],
#         success_url=request.build_absolute_uri(reverse("plans")) + "?paid=1",
#         cancel_url=request.build_absolute_uri(reverse("plans")),
#         metadata={
#             "user_id": request.user.id,
#             "plan_id": plan.id,
#         },
#     )
#     return Response({"checkout_url": session.url})


# 1. List plans
class PlanList(generics.ListAPIView):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = PlanSerializer


# 2. Subscribe
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe(request):
    plan_id = request.data.get("plan_id")
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    # delete old sub if exists
    Subscription.objects.filter(user=request.user).delete()

    sub = Subscription.create(request.user, plan)
    return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


# 3. Cancel
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel(request):
    sub = getattr(request.user, "subscription", None)
    if not sub or not sub.active:
        return Response({"detail": "No active subscription."}, status=400)

    sub.active = False
    sub.end = timezone.now()
    sub.save()
    return Response({"detail": "Canceled."})


# 4. Status
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    sub = getattr(request.user, "subscription", None)
    if not sub:
        return Response({"detail": "No subscription."}, status=404)
    return Response(SubscriptionSerializer(sub).data)


# 5. Dummy premium endpoint
@api_view(["GET"])
@permission_classes([IsAuthenticated, HasActiveSubscription])
def premium_hello(request):
    return Response({"message": f"Hi {request.user.username}, premium content unlocked!"})
