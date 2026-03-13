from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password_hash: str = Field()
    role: str = Field()  # "doctor" | "admin"
    full_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    institution: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    clinical_prompt: str = Field(default="")
    modality: str = "text+image"

    outputs: list["ModelOutput"] = Relationship(back_populates="case")


class ModelOutput(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id")
    model_name: str
    text_output: str
    image_url: Optional[str] = None

    case: Optional[Case] = Relationship(back_populates="outputs")
    evaluations: list["Evaluation"] = Relationship(back_populates="output")


class Evaluation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    output_id: int = Field(foreign_key="modeloutput.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    annotator_id: str
    overall_quality: int = Field(ge=0, le=5)  # 0 = non compilato
    clinical_accuracy: int = Field(ge=0, le=5)
    completeness: int = Field(ge=0, le=5)
    safety: int = Field(ge=0, le=5)
    preferred_for_case: bool = False
    hallucination: bool = False
    missing_important_findings: bool = False
    formatting_issues: bool = False
    safety_concerns: bool = False
    free_text_feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    output: Optional[ModelOutput] = Relationship(back_populates="evaluations")


class EvaluationROI(SQLModel, table=True):
    """Region-of-interest annotation on an image (output)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    output_id: int = Field(foreign_key="modeloutput.id")
    user_id: int = Field(foreign_key="users.id")
    annotator_id: str = Field()
    points_json: str = Field()  # JSON array of {x,y} or [{x,y},...] for polygon
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HelpRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    from_user_id: int = Field(foreign_key="users.id")
    to_role: str = Field()  # e.g. "admin"
    subject: str
    question: str
    answer: Optional[str] = Field(default=None)
    status: str = Field(default="open")  # "open" | "answered"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    answered_at: Optional[datetime] = Field(default=None)


class RegisteredModel(SQLModel, table=True):
    """Simple registry of models (admin)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    version: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    created_by_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

