from rest_framework import serializers
from .models import SubscriptionPlan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ("id", "name", "price", "interval_days")


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer()

    class Meta:
        model = Subscription
        fields = ("plan", "start", "end", "active")
