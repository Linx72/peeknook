"""PeekNook Cloud teams."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.billing import PLANS
from api.database import get_db
from api.deps import ensure_subscription, get_current_user
from api.models import Subscription, Team, TeamMember, User

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class MemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member)$")


def _team_limit(user: User, db: Session) -> int:
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    plan_id = sub.plan_id if sub else "free"
    return PLANS.get(plan_id, PLANS["free"])["teams"]


def _require_membership(team_id: str, user: User, db: Session, admin: bool = False) -> TeamMember:
    member = db.scalar(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
    )
    if not member:
        raise HTTPException(403, "Not a team member")
    if admin and member.role not in ("owner", "admin"):
        raise HTTPException(403, "Admin role required")
    return member


@router.post("")
def create_team(
    body: TeamCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_subscription(user, db)
    owned = db.scalar(
        select(Team).where(Team.owner_id == user.id)
    )
    limit = _team_limit(user, db)
    if limit == 0:
        raise HTTPException(402, "Teams require Pro or Team plan")
    if owned and limit <= 1:
        existing_count = db.scalar(
            select(TeamMember.team_id).where(TeamMember.user_id == user.id)
        )
        if existing_count:
            pass  # allow multiple memberships; limit owned teams below
    owned_count = len(db.scalars(select(Team).where(Team.owner_id == user.id)).all())
    if owned_count >= max(1, limit):
        raise HTTPException(402, f"Team limit reached ({limit})")

    team_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    team = Team(id=team_id, name=body.name, owner_id=user.id, created_at=now)
    member = TeamMember(
        id=str(uuid.uuid4()),
        team_id=team_id,
        user_id=user.id,
        role="owner",
        joined_at=now,
    )
    db.add(team)
    db.add(member)
    db.commit()
    return {"id": team_id, "name": body.name, "role": "owner"}


@router.get("")
def list_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Team, TeamMember.role)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user.id)
    ).all()
    return [
        {"id": team.id, "name": team.name, "role": role, "owner_id": team.owner_id}
        for team, role in rows
    ]


@router.get("/{team_id}")
def get_team(
    team_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_membership(team_id, user, db)
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    members = db.scalars(select(TeamMember).where(TeamMember.team_id == team_id)).all()
    out = []
    for m in members:
        u = db.get(User, m.user_id)
        out.append(
            {
                "user_id": m.user_id,
                "email": u.email if u else None,
                "role": m.role,
                "joined_at": m.joined_at.isoformat(),
            }
        )
    return {"id": team.id, "name": team.name, "members": out}


@router.post("/{team_id}/members")
def add_member(
    team_id: str,
    body: MemberAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_membership(team_id, user, db, admin=True)
    invitee = db.scalar(select(User).where(User.email == body.email.lower()))
    if not invitee:
        raise HTTPException(404, "User not registered — ask them to sign up first")
    exists = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.user_id == invitee.id
        )
    )
    if exists:
        raise HTTPException(400, "Already a member")
    member = TeamMember(
        id=str(uuid.uuid4()),
        team_id=team_id,
        user_id=invitee.id,
        role=body.role,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(member)
    db.commit()
    return {"team_id": team_id, "user_id": invitee.id, "email": invitee.email, "role": body.role}
