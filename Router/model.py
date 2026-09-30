# """Request / response schemas for the API."""
# from pydantic import BaseModel, Field


# class ChatRequest(BaseModel):
#     session_id: str = Field(default="default", description="Conversation id; history is kept per session")
#     query: str = Field(min_length=1)


# class ChatResponse(BaseModel):
#     session_id: str
#     route: str
#     company: str | None
#     standalone_query: str
#     answer: str
#     citations: list[dict]
#     filters_used: dict
#     latency_seconds: float


"""Request / response schemas for the API."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(default="default", description="Conversation id; history is kept per session")
    query: str = Field(min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    route: str
    company: str | None
    standalone_query: str
    answer: str
    citations: list[dict]
    metadata_summary: dict = {}
    filters_used: dict
    latency_seconds: float