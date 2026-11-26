import os
import hmac
import hashlib
import requests

from fastapi import HTTPException


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv(
    "RAZORPAY_WEBHOOK_SECRET"
)

RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"


def check_razorpay_config():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Razorpay credentials are not configured.",
        )


def razorpay_request(method, endpoint, payload=None):
    check_razorpay_config()

    response = requests.request(
        method=method,
        url=f"{RAZORPAY_BASE_URL}{endpoint}",
        json=payload,
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        timeout=20,
    )

    if not response.ok:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Razorpay API request failed",
                "razorpay_status": response.status_code,
            },
        )

    return response.json()


def create_razorpay_subscription(
    plan_id: str,
    user_id: int,
    plan_code: str,
):
    return razorpay_request(
        "POST",
        "/subscriptions",
        {
            "plan_id": plan_id,
            "total_count": 100,
            "customer_notify": 1,
            "notes": {
                "proofly_user_id": str(user_id),
                "proofly_plan_code": plan_code,
            },
        },
    )


def verify_checkout_signature(
    payment_id: str,
    subscription_id: str,
    signature: str,
):
    check_razorpay_config()

    message = f"{payment_id}|{subscription_id}"

    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature,
    )


def verify_webhook_signature(
    raw_body: bytes,
    signature: str,
):
    if not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Razorpay webhook secret is not configured.",
        )

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature,
    )


def cancel_razorpay_subscription(
    subscription_id: str,
    cancel_at_cycle_end: bool,
):
    return razorpay_request(
        "POST",
        f"/subscriptions/{subscription_id}/cancel",
        {
            "cancel_at_cycle_end": cancel_at_cycle_end,
        },
    )


def resume_razorpay_subscription(subscription_id: str):
    return razorpay_request(
        "POST",
        f"/subscriptions/{subscription_id}/resume",
        {
            "resume_at": "now",
        },
    )