"""Feedback request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FeedbackCreateRequest(BaseModel):
    """Payload submitted by a technician to evaluate or verify an alert or prediction."""

    prediction_id: int | None = Field(None, description="Linked prediction ID being verified")
    alert_id: int | None = Field(None, description="Linked alert ID being verified")
    feedback_type: str | None = Field(
        None, description="Label classification: CONFIRMED or FALSE_ALARM"
    )
    ground_truth_failure: bool | None = Field(
        None, description="True if real failure occurred, False if false positive"
    )
    notes: str | None = Field(
        None, description="Inspection notes, teardown findings, or explanation"
    )
    technician_id: str | None = Field(None, description="Technician or operator identifier")

    @model_validator(mode="after")
    def validate_reference_and_type(self) -> FeedbackCreateRequest:
        if self.prediction_id is None and self.alert_id is None:
            raise ValueError("Either prediction_id or alert_id must be provided")

        if self.feedback_type is None and self.ground_truth_failure is None:
            raise ValueError("Either feedback_type or ground_truth_failure must be provided")

        if self.feedback_type is not None:
            normalized = self.feedback_type.upper().strip()
            if normalized not in ("CONFIRMED", "FALSE_ALARM"):
                raise ValueError("feedback_type must be either 'CONFIRMED' or 'FALSE_ALARM'")
            self.feedback_type = normalized
        elif self.ground_truth_failure is not None:
            self.feedback_type = "CONFIRMED" if self.ground_truth_failure else "FALSE_ALARM"

        return self


class FeedbackDTO(BaseModel):
    """Persisted feedback record DTO."""

    id: int = Field(..., description="Unique feedback ID")
    machine_id: str = Field(..., description="Target machine identifier")
    alert_id: int | None = Field(None, description="Linked alert ID")
    feedback_type: str = Field(..., description="Classification: CONFIRMED or FALSE_ALARM")
    notes: str | None = Field(None, description="Technician notes")
    user_id: str | None = Field(None, description="Technician or operator ID")
    created_at: datetime = Field(..., description="Feedback creation timestamp")

    model_config = ConfigDict(from_attributes=True)
