from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class TicketCreate(BaseModel):
    source_email: str
    subject: str
    body: str


class Ticket(BaseModel):
    id: int
    source_email: str
    subject: str
    body: str
    type: Optional[str]
    urgency: Optional[str]
    status: str
    created_at: datetime


class WebhookPayload(BaseModel):
    email: str
    subject: str
    body: str
    timestamp: int


class ClassifyResult(BaseModel):
    type: str
    urgency: str
    confidence: float


class KBChunk(BaseModel):
    id: int
    document_name: str
    chunk_text: str
    score: float


class DraftResponse(BaseModel):
    ticket_id: int
    draft_text: str
    sources_used: list[dict]
    confidence_score: float


class ApproveRequest(BaseModel):
    agent_name: Optional[str] = "agent"
