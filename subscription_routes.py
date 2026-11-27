import os
import json
import hashlib

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from security import get_current_user

from models import (
    User,
    Subscription,
    SubscriptionPayment,
    RazorpayWebhookEvent,
)

from schemas import (
    CheckoutRequest,
    VerifyPaymentRequest,
    CancelSubscriptionRequest,
)

from subscription_service import (
    PLANS,
    get_user_subscription,
    subscription_has_access,
)

from models import (
    Business,
    PortfolioProject,
    Product,
    Testimonial,
)

from razorpay_service import (
    RAZORPAY_KEY_ID,
    create_razorpay_subscription,
    verify_checkout_signature,
    verify_webhook_signature,
    cancel_razorpay_subscription,
    resume_razorpay_subscription,
)
from subscription_service import get_entitlement

router = APIRouter(
    prefix="/api/v1/subscription",
    tags=["Subscription"],
)

@router.get("/plans")
def get_plans():
    return {
        "plans": [
            {
                "code": "pro",
                "name": "Pro",
                "price": 199,
                "currency": "INR",
                "interval": "monthly",
            },
            {
                "code": "business",
                "name": "Business",
                "price": 499,
                "currency": "INR",
                "interval": "monthly",
            },
        ]
    }


@router.get("/me")
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = get_user_subscription(
        db,
        current_user.id,
    )

    if not subscription:
        return {
            "subscription": None,
            "has_access": False,
        }

    return {
        "subscription": {
            "plan_code": subscription.plan_code,
            "status": subscription.status,
            "trial_end": subscription.trial_end,
            "current_start": subscription.current_start,
            "current_end": subscription.current_end,
            "cancel_at_cycle_end": (
                subscription.cancel_at_cycle_end
            ),
            "razorpay_subscription_id": (
                subscription.razorpay_subscription_id
            ),
        },
        "has_access": subscription_has_access(
            subscription
        ),
    }


@router.post("/checkout")
def create_checkout(
    data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = PLANS.get(data.plan_code)

    if not plan:
        raise HTTPException(
            status_code=400,
            detail="Invalid subscription plan.",
        )

    plan_id = os.getenv(plan["plan_id_env"])

    if not plan_id:
        raise HTTPException(
            status_code=503,
            detail=f"Razorpay plan ID missing for {data.plan_code}.",
        )

    # Prevent creating another subscription while
    # an existing paid subscription is active.
    current = get_user_subscription(
        db,
        current_user.id,
    )

    if current and current.status in (
        "created",
        "active",
        "authenticated",
        "pending",
    ):
        raise HTTPException(
            status_code=400,
            detail="You already have a subscription in progress.",
        )

    razorpay_subscription = create_razorpay_subscription(
        plan_id=plan_id,
        user_id=current_user.id,
        plan_code=data.plan_code,
    )

    subscription = Subscription(
        user_id=current_user.id,
        plan_code=data.plan_code,
        status=razorpay_subscription.get(
            "status",
            "created",
        ),
        razorpay_subscription_id=(
            razorpay_subscription["id"]
        ),
        cancel_at_cycle_end=False,
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return {
        "subscription_id": razorpay_subscription["id"],
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "plan_code": data.plan_code,
        "amount": plan["amount"],
        "currency": plan["currency"],
        "status": subscription.status,
    }


@router.post("/verify")
def verify_payment(
    data: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.razorpay_subscription_id
            == data.razorpay_subscription_id,
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found.",
        )

    valid_signature = verify_checkout_signature(
        payment_id=data.razorpay_payment_id,
        subscription_id=data.razorpay_subscription_id,
        signature=data.razorpay_signature,
    )

    if not valid_signature:
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay checkout signature.",
        )

    # Checkout signature is valid.
    # Webhook will confirm the final subscription state.
    subscription.status = "authenticated"

    db.commit()
    db.refresh(subscription)

    return {
        "verified": True,
        "message": "Checkout signature verified.",
        "subscription_status": subscription.status,
        "note": "Waiting for Razorpay subscription webhook.",
    }


@router.post("/cancel")
def cancel_subscription(
    data: CancelSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = get_user_subscription(
        db,
        current_user.id,
    )

    if not subscription or not subscription.razorpay_subscription_id:
        raise HTTPException(
            status_code=404,
            detail="Paid subscription not found.",
        )

    result = cancel_razorpay_subscription(
        subscription_id=(
            subscription.razorpay_subscription_id
        ),
        cancel_at_cycle_end=data.cancel_at_cycle_end,
    )

    if data.cancel_at_cycle_end:
        # Keep access until the paid period ends.
        subscription.cancel_at_cycle_end = True
    else:
        subscription.status = "cancelled"
        subscription.cancel_at_cycle_end = False

    db.commit()

    return {
        "message": "Subscription cancellation requested.",
        "cancel_at_cycle_end": data.cancel_at_cycle_end,
        "razorpay_status": result.get("status"),
    }


@router.post("/resume")
def resume_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = get_user_subscription(
        db,
        current_user.id,
    )

    if not subscription or not subscription.razorpay_subscription_id:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found.",
        )

    result = resume_razorpay_subscription(
        subscription.razorpay_subscription_id
    )

    subscription.cancel_at_cycle_end = False

    db.commit()

    return {
        "message": "Resume request sent to Razorpay.",
        "razorpay_status": result.get("status"),
    }


@router.get("/payments")
def get_payment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payments = (
        db.query(SubscriptionPayment)
        .filter(
            SubscriptionPayment.user_id == current_user.id
        )
        .order_by(
            SubscriptionPayment.created_at.desc()
        )
        .all()
    )

    return {
        "payments": [
            {
                "razorpay_payment_id": p.razorpay_payment_id,
                "amount": float(p.amount),
                "currency": p.currency,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in payments
        ]
    }

webhook_router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["Payment Webhooks"],
)


def timestamp_to_datetime(value):
    if not value:
        return None

    return datetime.fromtimestamp(
        int(value),
        tz=timezone.utc,
    )


@webhook_router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay webhook signature.",
        )

    if not verify_webhook_signature(
        raw_body,
        signature,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature.",
        )

    payload = json.loads(raw_body)

    event_type = payload.get("event", "")
    event_id = request.headers.get(
        "X-Razorpay-Event-Id"
    )

    # Fallback event ID if the header is not provided.
    if not event_id:
        event_id = hashlib.sha256(
            raw_body
        ).hexdigest()

    existing_event = (
        db.query(RazorpayWebhookEvent)
        .filter(
            RazorpayWebhookEvent.event_id == event_id
        )
        .first()
    )

    if existing_event:
        return {
            "received": True,
            "duplicate": True,
        }

    event_record = RazorpayWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
    )

    db.add(event_record)

    entity = (
        payload.get("payload", {})
        .get("subscription", {})
        .get("entity", {})
    )

    subscription_id = entity.get("id")

    subscription = None

    if subscription_id:
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.razorpay_subscription_id
                == subscription_id
            )
            .first()
        )

    if subscription:
        # Update subscription period when supplied.
        subscription.current_start = (
            timestamp_to_datetime(
                entity.get("current_start")
            )
            or subscription.current_start
        )

        subscription.current_end = (
            timestamp_to_datetime(
                entity.get("current_end")
            )
            or subscription.current_end
        )

        if event_type == "subscription.authenticated":
            subscription.status = "authenticated"

        elif event_type == "subscription.activated":
            subscription.status = "active"

        elif event_type == "subscription.charged":
            subscription.status = "active"

        elif event_type == "subscription.pending":
            subscription.status = "pending"

        elif event_type == "subscription.halted":
            subscription.status = "past_due"

        elif event_type == "subscription.cancelled":
            subscription.status = "cancelled"
            subscription.cancel_at_cycle_end = False

        elif event_type == "subscription.completed":
            subscription.status = "completed"

        elif event_type == "subscription.paused":
            subscription.status = "paused"

        elif event_type == "subscription.resumed":
            subscription.status = "active"

        # Save recurring payment record from charged event.
        if event_type == "subscription.charged":
            payment_entity = (
                payload.get("payload", {})
                .get("payment", {})
                .get("entity", {})
            )

            payment_id = payment_entity.get("id")

            if payment_id:
                existing_payment = (
                    db.query(SubscriptionPayment)
                    .filter(
                        SubscriptionPayment.razorpay_payment_id
                        == payment_id
                    )
                    .first()
                )

                if not existing_payment:
                    amount_paise = payment_entity.get(
                        "amount",
                        0,
                    )

                    payment = SubscriptionPayment(
                        user_id=subscription.user_id,
                        subscription_id=subscription.id,
                        razorpay_payment_id=payment_id,
                        amount=amount_paise / 100,
                        currency=payment_entity.get(
                            "currency",
                            "INR",
                        ),
                        status=payment_entity.get(
                            "status",
                            "captured",
                        ),
                    )

                    db.add(payment)

    db.commit()

    return {
        "received": True,
        "event": event_type,
    }


def _get_usage_snapshot(db: Session, user_id: int, features: dict):
    business_ids = [
        row[0]
        for row in db.query(Business.id)
        .filter(Business.user_id == user_id)
        .all()
    ]

    def count_items(model):
        if not business_ids:
            return 0

        return (
            db.query(func.count(model.id))
            .filter(model.business_id.in_(business_ids))
            .scalar()
            or 0
        )

    counts = {
        "portfolio": count_items(PortfolioProject),
        "products": count_items(Product),
        "testimonials": count_items(Testimonial),
    }

    limits = {
        "portfolio": features["portfolio_limit"],
        "products": features["product_limit"],
        "testimonials": features["testimonial_limit"],
    }

    usage = {}

    for feature, current in counts.items():
        limit = limits[feature]

        usage[feature] = {
            "used": current,
            "limit": limit,
            "remaining": (
                None if limit is None
                else max(limit - current, 0)
            ),
            "unlimited": limit is None,
        }

    return usage

@router.post("/trial")
def start_free_trial(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_trial = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.plan == "free_trial",
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if existing_trial:
        entitlement = get_entitlement(db, current_user.id)

        if not entitlement["has_access"]:
            raise HTTPException(
                status_code=409,
                detail="Your free trial has already expired or been used.",
            )

        return {
            "message": "Your free trial is already available.",
            "status": existing_trial.status,
            "trial_ends_at": existing_trial.trial_ends_at,
            "has_access": entitlement["has_access"],
        }

    paid_subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.plan.in_(["pro", "business"]),
        )
        .first()
    )

    if paid_subscription:
        raise HTTPException(
            status_code=409,
            detail="A paid subscription already exists for this account.",
        )

    trial = ensure_trial_record(db, current_user)
    db.commit()
    db.refresh(trial)

    entitlement = get_entitlement(db, current_user.id)

    if not entitlement["has_access"]:
        raise HTTPException(
            status_code=409,
            detail="Your free trial eligibility has expired.",
        )

    return {
        "message": "Free trial is available.",
        "plan": "pro",
        "status": trial.status,
        "trial_started_at": trial.trial_started_at,
        "trial_ends_at": trial.trial_ends_at,
        "has_access": entitlement["has_access"],
    }


@router.get("/usage")
def get_subscription_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    businesses = db.query(Business.id).filter(
        Business.user_id == current_user.id
    ).all()

    business_ids = [business.id for business in businesses]

    portfolio_count = 0
    product_count = 0
    testimonial_count = 0

    if business_ids:
        portfolio_count = db.query(PortfolioProject).filter(
            PortfolioProject.business_id.in_(business_ids)
        ).count()

        product_count = db.query(Product).filter(
            Product.business_id.in_(business_ids)
        ).count()

        testimonial_count = db.query(Testimonial).filter(
            Testimonial.business_id.in_(business_ids)
        ).count()

    entitlement = get_entitlement(db, current_user.id)
    limits = entitlement["limits"]

    return {
        "plan": entitlement["plan"],
        "has_access": entitlement["has_access"],
        "usage": {
            "portfolio": portfolio_count,
            "products": product_count,
            "testimonials": testimonial_count,
        },
        "limits": limits,
    }

@router.get("/permissions")
def get_subscription_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entitlement = get_entitlement(db, current_user.id)

    return {
        "plan": entitlement["plan"],
        "status": entitlement["status"],
        "has_access": entitlement["has_access"],
        "permissions": {
            "can_publish": entitlement["has_access"],
            "can_create_portfolio": entitlement["has_access"],
            "can_create_products": entitlement["has_access"],
            "can_create_testimonials": entitlement["has_access"],
        },
        "limits": entitlement["limits"],
    }


@router.get("/status")
def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = get_user_subscription(db, current_user.id)
    entitlement = get_entitlement(db, current_user.id)

    return {
        "plan": entitlement["plan"],
        "status": entitlement["status"],
        "has_access": entitlement["has_access"],
        "trial_end": subscription.trial_end if subscription else None,
        "current_start": subscription.current_start if subscription else None,
        "current_end": subscription.current_end if subscription else None,
        "cancel_at_cycle_end": (
            subscription.cancel_at_cycle_end if subscription else False
        ),
    }


@router.get("/invoices")
def get_subscription_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(SubscriptionPayment)
        .filter(
            SubscriptionPayment.user_id == current_user.id
        )
        .order_by(SubscriptionPayment.created_at.desc())
        .limit(100)
        .all()
    )

    return {
        "invoices": [
            {
                "id": row.id,
                "invoice_id": row.razorpay_invoice_id,
                "payment_id": row.razorpay_payment_id,
                "subscription_id": row.subscription_id,
                "amount": float(row.amount),
                "currency": row.currency,
                "status": row.status,
                "paid_at": row.paid_at,
                "created_at": row.created_at,
                "invoice_available": bool(row.razorpay_invoice_id),
            }
            for row in rows
        ]
    }