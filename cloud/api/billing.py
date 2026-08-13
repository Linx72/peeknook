"""PeekNook Cloud billing — plans, subscriptions, usage limits."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.deps import ensure_subscription, get_current_user
from api.models import BlobRecord, Subscription, SyncEvent, User

router = APIRouter(prefix="/billing", tags=["billing"])

PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "storage_bytes": 100 * 1024 * 1024,
        "sync_events_month": 1_000,
        "teams": 0,
    },
    "pro": {
        "name": "Pro",
        "price_usd": 9,
        "storage_bytes": 10 * 1024 * 1024 * 1024,
        "sync_events_month": 100_000,
        "teams": 1,
    },
    "team": {
        "name": "Team",
        "price_usd": 29,
        "storage_bytes": 50 * 1024 * 1024 * 1024,
        "sync_events_month": 500_000,
        "teams": 10,
    },
}


class CheckoutRequest(BaseModel):
    plan_id: str = Field(pattern="^(pro|team)$")


def _plan_limits(plan_id: str) -> Dict[str, Any]:
    return PLANS.get(plan_id, PLANS["free"])


def check_storage_limit(user: User, db: Session, extra_bytes: int = 0) -> None:
    sub = ensure_subscription(user, db)
    limits = _plan_limits(sub.plan_id)
    used = db.scalar(
        select(func.coalesce(func.sum(BlobRecord.size_bytes), 0)).where(
            BlobRecord.user_id == user.id
        )
    ) or 0
    if used + extra_bytes > limits["storage_bytes"]:
        raise HTTPException(
            402,
            f"Storage limit exceeded for {sub.plan_id} plan. Upgrade at /billing/checkout",
        )


def check_sync_limit(user: User, db: Session, new_events: int = 1) -> None:
    sub = ensure_subscription(user, db)
    limits = _plan_limits(sub.plan_id)
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = db.scalar(
        select(func.count())
        .select_from(SyncEvent)
        .where(SyncEvent.user_id == user.id, SyncEvent.created_at >= month_start)
    ) or 0
    if count + new_events > limits["sync_events_month"]:
        raise HTTPException(402, f"Monthly sync limit exceeded for {sub.plan_id} plan")


@router.get("/plans")
def list_plans():
    return {"plans": [{"id": k, **v} for k, v in PLANS.items()]}


@router.get("/config")
def billing_config():
    """Whether live Stripe checkout is configured (secrets present)."""
    return {
        "stripe_live": bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_PRICE_PRO")),
        "stripe_webhook": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
    }


@router.get("/subscription")
def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = ensure_subscription(user, db)
    limits = _plan_limits(sub.plan_id)
    storage_used = db.scalar(
        select(func.coalesce(func.sum(BlobRecord.size_bytes), 0)).where(
            BlobRecord.user_id == user.id
        )
    ) or 0
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sync_used = db.scalar(
        select(func.count())
        .select_from(SyncEvent)
        .where(SyncEvent.user_id == user.id, SyncEvent.created_at >= month_start)
    ) or 0
    return {
        "plan_id": sub.plan_id,
        "plan": limits,
        "status": sub.status,
        "usage": {
            "storage_bytes": storage_used,
            "storage_limit_bytes": limits["storage_bytes"],
            "sync_events_month": sync_used,
            "sync_limit_month": limits["sync_events_month"],
        },
    }


@router.post("/checkout")
def checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Checkout — Stripe session when configured, otherwise dev instant upgrade."""
    if body.plan_id not in PLANS or body.plan_id == "free":
        raise HTTPException(400, "Invalid plan")
    sub = ensure_subscription(user, db)
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    price_id = os.getenv(f"STRIPE_PRICE_{body.plan_id.upper()}")

    if stripe_key and price_id:
        try:
            import stripe

            stripe.api_key = stripe_key
            customer_id = sub.stripe_customer_id
            if not customer_id or str(customer_id).startswith("cus_stub_"):
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={"user_id": user.id},
                )
                customer_id = customer.id
                sub.stripe_customer_id = customer_id
                db.commit()

            success_url = os.getenv(
                "STRIPE_SUCCESS_URL",
                "http://127.0.0.1:8090/?checkout=success",
            )
            cancel_url = os.getenv(
                "STRIPE_CANCEL_URL",
                "http://127.0.0.1:8090/?checkout=cancel",
            )
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user.id,
                metadata={"user_id": user.id, "plan_id": body.plan_id},
            )
            return {
                "upgraded": False,
                "plan_id": body.plan_id,
                "message": "Redirect to Stripe Checkout",
                "checkout_url": session.url,
            }
        except Exception as exc:
            raise HTTPException(502, f"Stripe checkout failed: {exc}") from exc

    sub.plan_id = body.plan_id
    sub.status = "active"
    sub.updated_at = datetime.now(timezone.utc)
    if stripe_key:
        sub.stripe_customer_id = sub.stripe_customer_id or f"cus_stub_{uuid.uuid4().hex[:12]}"
    db.commit()
    return {
        "upgraded": True,
        "plan_id": body.plan_id,
        "message": "Plan upgraded (dev mode — set STRIPE_PRICE_PRO / STRIPE_PRICE_TEAM for live checkout)",
        "checkout_url": None,
    }


@router.post("/cancel")
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = ensure_subscription(user, db)
    sub.plan_id = "free"
    sub.status = "active"
    sub.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"plan_id": "free", "status": "active"}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook stub — verify signature in production (STRIPE_WEBHOOK_SECRET).
    Handles checkout.session.completed → upgrade plan.
    """
    import os

    payload = await request.body()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if secret:
        sig = request.headers.get("stripe-signature", "")
        if not sig:
            raise HTTPException(400, "Missing stripe-signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Invalid JSON") from exc

    etype = event.get("type")
    if etype == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id")
        plan_id = session.get("metadata", {}).get("plan_id", "pro")
        if user_id:
            sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
            if sub:
                sub.plan_id = plan_id
                sub.status = "active"
                sub.stripe_customer_id = session.get("customer")
                sub.updated_at = datetime.now(timezone.utc)
                db.commit()
    return {"received": True, "type": etype}
