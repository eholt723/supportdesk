"""
Classify a support ticket by type and urgency using Groq LLM.
Returns type, urgency, and confidence score.
"""
import json
import re

from groq import AsyncGroq

from app.config import settings

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


CLASSIFY_PROMPT = """\
You are a customer support triage system. Classify the support ticket below.

Respond with a JSON object only — no explanation, no markdown — using exactly this structure:
{{"type": "<type>", "urgency": "<urgency>", "confidence": <float 0.0-1.0>}}

Valid types: billing, technical, feature_request, escalation, general
Valid urgency levels: low, medium, high

Rules:
- billing: questions or issues about charges, refunds, cancellation, plan changes
- technical: product bugs, broken features, errors, integrations not working
- feature_request: asking about features, plan capabilities, what is included
- escalation: user is angry, threatening to leave, reporting SLA breach, mentions previous unanswered tickets
- general: anything that does not fit the above

Urgency:
- high: mentions urgency, deadline, legal threat, or multiple failed contacts
- medium: normal issue without urgency signals
- low: general inquiry, curiosity, non-blocking question

Ticket subject: {subject}
Ticket body: {body}"""


async def classify_ticket(subject: str, body: str) -> dict:
    client = _get_client()

    prompt = CLASSIFY_PROMPT.format(subject=subject, body=body)

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=128,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip("` \n")

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if LLM returns unexpected format
        result = {"type": "general", "urgency": "medium", "confidence": 0.5}

    # Validate and normalise
    valid_types = {"billing", "technical", "feature_request", "escalation", "general"}
    valid_urgencies = {"low", "medium", "high"}

    ticket_type = result.get("type", "general").lower()
    urgency = result.get("urgency", "medium").lower()
    confidence = float(result.get("confidence", 0.75))

    if ticket_type not in valid_types:
        ticket_type = "general"
    if urgency not in valid_urgencies:
        urgency = "medium"
    confidence = max(0.0, min(1.0, confidence))

    return {"type": ticket_type, "urgency": urgency, "confidence": confidence}
