from rest_framework.permissions import BasePermission
from django.utils import timezone


class HasActiveSubscription(BasePermission):
    """
    Allow access only if request.user has an active, non-expired subscription.
    """

    message = "Subscription required."

    def has_permission(self, request, view):
        sub = getattr(request.user, "subscription", None)
        return sub and sub.active and sub.end > timezone.now()
