from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Subscription


TRIAL_DAYS = 30
GRACE_DAYS = 5

PLANS = {
    "pro": {
        "name": "Pro",
        "amount": 19900,  # ₹199 in paise
        "currency": "INR",
        "plan_id_env": "RAZORPAY_PRO_PLAN_ID",
        "limits": {
            "portfolio": 15,
            "products": 25,
            "testimonials": 20,
        },
    },
    "business": {
        "name": "Business",
        "amount": 49900,  # ₹499 in paise
        "currency": "INR",
        "plan_id_env": "RAZORPAY_BUSINESS_PLAN_ID",
        "limits": {
            "portfolio": None,
            "products": None,
            "testimonials": None,
        },
    },
}


def utc_now():
    return datetime.now(timezone.utc)


def get_user_subscription(db: Session, user_id: int):
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .first()
    )


def create_trial(db: Session, user_id: int):
    now = utc_now()

    subscription = Subscription(
        user_id=user_id,
        plan_code="free_trial",
        status="trialing",
        trial_start=now,
        trial_end=now + timedelta(days=TRIAL_DAYS),
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


def subscription_has_access(subscription):
    if not subscription:
        return False

    now = utc_now()

    # Free trial is valid until trial_end.
    if subscription.status == "trialing":
        return (
            subscription.trial_end is not None
            and subscription.trial_end > now
        )

    # Paid subscription is active.
    if subscription.status == "active":
        if subscription.current_end is None:
            return True

        return subscription.current_end > now

    # Optional grace period for a failed renewal.
    if subscription.status == "past_due":
        if subscription.current_end is None:
            return False

        grace_end = (
            subscription.current_end
            + timedelta(days=GRACE_DAYS)
        )

        return grace_end > now

    return False


def require_subscription_access(db: Session, user_id: int):
    subscription = get_user_subscription(db, user_id)

    if not subscription_has_access(subscription):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "SUBSCRIPTION_REQUIRED",
                "message": "Your trial or subscription has expired.",
            },
        )

    return subscription


def get_entitlement(db: Session, user_id: int):
    subscription = get_user_subscription(db, user_id)

    if not subscription:
        return {
            "plan": "free_trial",
            "status": "expired",
            "has_access": False,
            "limits": PLANS["pro"]["limits"],
        }

    plan_code = subscription.plan_code

    # Trial uses the Pro limits during the trial period
    limits_plan = "pro" if plan_code == "free_trial" else plan_code
    plan = PLANS.get(limits_plan)

    limits = (
        plan["limits"]
        if plan
        else {
            "portfolio": 0,
            "products": 0,
            "testimonials": 0,
        }
    )

    return {
        "plan": plan_code,
        "status": subscription.status,
        "has_access": subscription_has_access(subscription),
        "limits": limits,
    }