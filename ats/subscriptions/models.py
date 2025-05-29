from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class SubscriptionPlan(models.Model):
    name   = models.CharField(max_length=30, unique=True)
    price  = models.PositiveIntegerField()        # just a number; no payments yet
    interval_days = models.PositiveIntegerField() # 30 for monthly

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user   = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="subscription")
    plan   = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start  = models.DateTimeField(default=timezone.now)
    end    = models.DateTimeField()
    active = models.BooleanField(default=False)

    @classmethod
    def create(cls, user, plan):
        now = timezone.now()
        return cls.objects.create(
            user=user,
            plan=plan,
            start=now,
            end=now + timedelta(days=plan.interval_days),
            active=True,
        )
