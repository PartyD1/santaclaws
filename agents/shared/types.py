"""Typed rows shared by Mainstreet NemoClaw claws."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID


QualStatus = Literal[
    "pending",
    "qualified_for_mockup",
    "qualified_for_rebuild",
    "qualified_for_receptionist",
    "skip",
]
ClawName = Literal["scout", "designer", "pitcher", "closer"]
ActionStatus = Literal["started", "succeeded", "failed", "skipped"]
Variant = Literal["clean_modern", "retro_local", "premium"]
Angle = Literal["specific_pain", "competitor_comparison", "social_proof", "curiosity"]
OutreachStatus = Literal["pending_approval", "approved", "sent", "skipped", "failed"]
Classification = Literal[
    "interested",
    "not_interested",
    "has_question",
    "has_objection",
    "spam",
    "uncertain",
]
Channel = Literal["email", "voice"]
ApprovalTarget = Literal["outreach", "inbound_reply"]
ApprovalDecision = Literal["approve", "edit", "skip", "escalate"]
MeetingStatus = Literal["booked", "completed", "cancelled"]


def _uuid(value: Any) -> UUID:
    """Convert Supabase UUID strings to UUID objects."""

    return value if isinstance(value, UUID) else UUID(str(value))


def _optional_uuid(value: Any) -> UUID | None:
    """Convert a nullable Supabase UUID value."""

    return None if value is None else _uuid(value)


def _dt(value: Any) -> datetime:
    """Convert Supabase timestamp strings to datetime objects."""

    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _optional_dt(value: Any) -> datetime | None:
    """Convert a nullable Supabase timestamp value."""

    return None if value is None else _dt(value)


def _string_list(value: Any) -> list[str]:
    """Normalize nullable Postgres text[] values."""

    if value is None:
        return []
    return [str(item) for item in value]


@dataclass(frozen=True)
class Lead:
    """A row from the `leads` table."""

    id: UUID
    business_name: str
    niche: str
    city: str
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    google_rating: float | None
    review_count: int
    review_texts: list[str]
    top_review_pain_points: list[str]
    website_score: int | None
    website_score_reasons: list[str]
    qualification_status: QualStatus
    qualification_reason: str | None
    worked_by_designer: bool
    worked_by_pitcher: bool
    do_not_contact: bool
    scraped_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Lead":
        """Build a Lead from a Supabase result row."""

        return cls(
            id=_uuid(row["id"]),
            business_name=str(row["business_name"]),
            niche=str(row["niche"]),
            city=str(row["city"]),
            address=row.get("address"),
            phone=row.get("phone"),
            email=row.get("email"),
            website=row.get("website"),
            google_rating=None if row.get("google_rating") is None else float(row["google_rating"]),
            review_count=int(row.get("review_count") or 0),
            review_texts=_string_list(row.get("review_texts")),
            top_review_pain_points=_string_list(row.get("top_review_pain_points")),
            website_score=None if row.get("website_score") is None else int(row["website_score"]),
            website_score_reasons=_string_list(row.get("website_score_reasons")),
            qualification_status=row.get("qualification_status", "pending"),
            qualification_reason=row.get("qualification_reason"),
            worked_by_designer=bool(row.get("worked_by_designer", False)),
            worked_by_pitcher=bool(row.get("worked_by_pitcher", False)),
            do_not_contact=bool(row.get("do_not_contact", False)),
            scraped_at=_optional_dt(row.get("scraped_at")),
            updated_at=_optional_dt(row.get("updated_at")),
        )


@dataclass(frozen=True)
class Action:
    """A row from the `actions` table."""

    id: UUID
    claw_name: ClawName
    lead_id: UUID | None
    action_type: str
    status: ActionStatus
    started_at: datetime | None
    finished_at: datetime | None
    result_json: dict[str, Any] | None
    human_readable_log: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Action":
        """Build an Action from a Supabase result row."""

        return cls(
            id=_uuid(row["id"]),
            claw_name=row["claw_name"],
            lead_id=_optional_uuid(row.get("lead_id")),
            action_type=str(row["action_type"]),
            status=row["status"],
            started_at=_optional_dt(row.get("started_at")),
            finished_at=_optional_dt(row.get("finished_at")),
            result_json=row.get("result_json"),
            human_readable_log=str(row["human_readable_log"]),
        )


@dataclass(frozen=True)
class GeneratedSite:
    """A row from the `generated_sites` table."""

    id: UUID
    lead_id: UUID
    variant: Variant
    vercel_url: str | None
    storage_url: str | None
    html_content: str
    self_critique_score: float | None
    self_critique_iterations: int
    critique_issues: list[str]
    is_chosen_winner: bool
    pick_reasoning: str | None
    generated_at: datetime | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "GeneratedSite":
        """Build a GeneratedSite from a Supabase result row."""

        return cls(
            id=_uuid(row["id"]),
            lead_id=_uuid(row["lead_id"]),
            variant=row["variant"],
            vercel_url=row.get("vercel_url"),
            storage_url=row.get("storage_url"),
            html_content=str(row["html_content"]),
            self_critique_score=(
                None if row.get("self_critique_score") is None else float(row["self_critique_score"])
            ),
            self_critique_iterations=int(row.get("self_critique_iterations") or 1),
            critique_issues=_string_list(row.get("critique_issues")),
            is_chosen_winner=bool(row.get("is_chosen_winner", False)),
            pick_reasoning=row.get("pick_reasoning"),
            generated_at=_optional_dt(row.get("generated_at")),
        )


@dataclass(frozen=True)
class Outreach:
    """A row from the `outreach` table."""

    id: UUID
    lead_id: UUID
    to_address: str | None
    angle: Angle
    subject: str
    body: str
    critique_score: float | None
    runner_up_variants: dict[str, Any] | None
    status: OutreachStatus
    drafted_at: datetime | None
    approved_at: datetime | None
    sent_at: datetime | None
    resend_message_id: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Outreach":
        """Build an Outreach row from Supabase data."""

        return cls(
            id=_uuid(row["id"]),
            lead_id=_uuid(row["lead_id"]),
            to_address=row.get("to_address"),
            angle=row["angle"],
            subject=str(row["subject"]),
            body=str(row["body"]),
            critique_score=None if row.get("critique_score") is None else float(row["critique_score"]),
            runner_up_variants=row.get("runner_up_variants"),
            status=row["status"],
            drafted_at=_optional_dt(row.get("drafted_at")),
            approved_at=_optional_dt(row.get("approved_at")),
            sent_at=_optional_dt(row.get("sent_at")),
            resend_message_id=row.get("resend_message_id"),
        )


@dataclass(frozen=True)
class Inbound:
    """A row from the `inbound` table."""

    id: UUID
    lead_id: UUID | None
    channel: Channel
    raw_content: str
    transcript: str | None
    from_address: str | None
    classification: Classification | None
    classification_confidence: int | None
    classification_key_phrase: str | None
    received_at: datetime | None
    handled_at: datetime | None
    handled_by: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Inbound":
        """Build an Inbound from a Supabase result row."""

        return cls(
            id=_uuid(row["id"]),
            lead_id=_optional_uuid(row.get("lead_id")),
            channel=row["channel"],
            raw_content=str(row["raw_content"]),
            transcript=row.get("transcript"),
            from_address=row.get("from_address"),
            classification=row.get("classification"),
            classification_confidence=(
                None if row.get("classification_confidence") is None else int(row["classification_confidence"])
            ),
            classification_key_phrase=row.get("classification_key_phrase"),
            received_at=_optional_dt(row.get("received_at")),
            handled_at=_optional_dt(row.get("handled_at")),
            handled_by=row.get("handled_by"),
        )


@dataclass(frozen=True)
class Meeting:
    """A row from the `meetings` table."""

    id: UUID
    lead_id: UUID
    inbound_id: UUID | None
    scheduled_for: datetime
    google_event_id: str | None
    status: MeetingStatus
    attendee_email: str | None
    booked_at: datetime | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Meeting":
        """Build a Meeting from a Supabase result row."""

        return cls(
            id=_uuid(row["id"]),
            lead_id=_uuid(row["lead_id"]),
            inbound_id=_optional_uuid(row.get("inbound_id")),
            scheduled_for=_dt(row["scheduled_for"]),
            google_event_id=row.get("google_event_id"),
            status=row["status"],
            attendee_email=row.get("attendee_email"),
            booked_at=_optional_dt(row.get("booked_at")),
        )


@dataclass(frozen=True)
class Approval:
    """A row from the `approvals` table."""

    id: UUID
    target_type: ApprovalTarget
    target_id: UUID
    decision: ApprovalDecision | None
    edit_payload: dict[str, Any] | None
    requested_at: datetime | None
    decided_at: datetime | None
    decided_by: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Approval":
        """Build an Approval from a Supabase result row."""

        return cls(
            id=_uuid(row["id"]),
            target_type=row["target_type"],
            target_id=_uuid(row["target_id"]),
            decision=row.get("decision"),
            edit_payload=row.get("edit_payload"),
            requested_at=_optional_dt(row.get("requested_at")),
            decided_at=_optional_dt(row.get("decided_at")),
            decided_by=row.get("decided_by"),
        )
