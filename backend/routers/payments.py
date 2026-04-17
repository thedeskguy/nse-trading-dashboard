import hashlib
import hmac
import json
import sys
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from config import get_settings
from deps import verify_supabase_jwt
from fastapi import Depends

router = APIRouter()


class CreateSubscriptionBody(BaseModel):
    plan: Literal["monthly", "annual"]


@router.get("/payments/subscription-status")
async def get_subscription_status(
    user: dict = Depends(verify_supabase_jwt),
):
    """Return the authenticated user's current subscription status."""
    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        # No Supabase service role configured — treat as free
        return {"plan": "free", "status": "inactive", "current_period_end": None}

    try:
        from supabase import create_client

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        result = (
            supabase.table("subscriptions")
            .select("status, current_period_end, plan_id")
            .eq("user_id", user["user_id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        rows = result.data
        if not rows:
            return {"plan": "free", "status": "inactive", "current_period_end": None}

        row = rows[0]
        is_active = row["status"] == "active"
        return {
            "plan": "pro" if is_active else "free",
            "status": row["status"],
            "current_period_end": row.get("current_period_end"),
        }

    except Exception as e:
        # Don't expose internals — return free gracefully
        print(f"subscription-status error: {e}")
        return {"plan": "free", "status": "inactive", "current_period_end": None}


@router.post("/payments/create-subscription")
async def create_subscription(
    body: CreateSubscriptionBody,
    user: dict = Depends(verify_supabase_jwt),
):
    """Create a Razorpay subscription for the authenticated user."""
    settings = get_settings()

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    plan_id = (
        settings.RAZORPAY_PLAN_ID_MONTHLY
        if body.plan == "monthly"
        else settings.RAZORPAY_PLAN_ID_ANNUAL
    )

    if not plan_id:
        raise HTTPException(
            status_code=503,
            detail=f"Plan ID for '{body.plan}' is not configured",
        )

    try:
        import razorpay

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        subscription = client.subscription.create(
            {
                "plan_id": plan_id,
                "total_count": 12 if body.plan == "monthly" else 1,
                "quantity": 1,
                "notes": {
                    "user_id": user["user_id"],
                    "email": user.get("email", ""),
                },
            }
        )

        return {
            "subscription_id": subscription["id"],
            "short_url": subscription.get("short_url"),
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to create subscription: {e}")


@router.post("/payments/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(...),
):
    """
    Handle Razorpay webhook events.
    Verifies HMAC-SHA256 signature and processes subscription lifecycle events.
    Not protected by JWT — this is a server-to-server webhook.
    """
    settings = get_settings()

    raw_body = await request.body()

    # Verify HMAC-SHA256 signature
    if settings.RAZORPAY_WEBHOOK_SECRET:
        expected_sig = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, x_razorpay_signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})

    subscription_id = entity.get("id")
    customer_id = entity.get("customer_id")
    plan_id = entity.get("plan_id")
    current_start = entity.get("current_start")
    current_end = entity.get("current_end")
    notes = entity.get("notes", {})
    user_id = notes.get("user_id")

    # Process with Supabase if service role key is configured
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client

            supabase = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
            )

            if event == "subscription.activated":
                supabase.table("subscriptions").upsert(
                    {
                        "subscription_id": subscription_id,
                        "user_id": user_id,
                        "customer_id": customer_id,
                        "plan_id": plan_id,
                        "status": "active",
                        "current_period_start": current_start,
                        "current_period_end": current_end,
                    },
                    on_conflict="subscription_id",
                ).execute()

            elif event == "subscription.charged":
                supabase.table("subscriptions").update(
                    {
                        "current_period_end": current_end,
                        "current_period_start": current_start,
                        "status": "active",
                    }
                ).eq("subscription_id", subscription_id).execute()

            elif event == "subscription.cancelled":
                supabase.table("subscriptions").update(
                    {"status": "cancelled"}
                ).eq("subscription_id", subscription_id).execute()

        except Exception as e:
            # Log but don't fail — Razorpay expects 200 OK even on downstream errors
            print(f"Supabase update error for event '{event}': {e}")

    return {"received": True}
