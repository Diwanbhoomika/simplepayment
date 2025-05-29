from django.urls import path
from . import views

urlpatterns = [
    # JSON API
    path("plans/", views.PlanList.as_view()),
    path("subscribe/", views.subscribe),
    path("cancel/", views.cancel),
    path("subscription/", views.subscription_status),
    path("premium/", views.premium_hello),

    path("razorpay/create-order/", views.razorpay_create_order,
         name="razorpay_create_order"),
    path("razorpay/verify/", views.razorpay_verify, name="razorpay_verify"),
    path("thanks/", views.thank_you, name="thank_you"),
   
    # HTML pages
    path("", views.plans_page, name="plans"),
    path("me/", views.me_page, name="me"),
    path("subscribe-html/", views.subscribe_html, name="subscribe"),
    path("cancel-html/", views.cancel_html, name="cancel"),
    path("premium-demo/", views.premium_demo, name="premium_demo"),
]

