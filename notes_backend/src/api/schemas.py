from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    email: str = Field(..., description="User email", max_length=255)
    password: str = Field(..., description="Plaintext password (min 6 chars)", min_length=6, max_length=128)


class AuthLoginRequest(BaseModel):
    email: str = Field(..., description="User email", max_length=255)
    password: str = Field(..., description="Plaintext password", min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int = Field(..., description="User id")
    email: str = Field(..., description="User email")
    created_at: datetime = Field(..., description="Created timestamp")


class AuthResponse(BaseModel):
    token: str = Field(..., description="JWT bearer token")
    user: UserOut = Field(..., description="User profile")


class TagCreateRequest(BaseModel):
    name: str = Field(..., description="Tag name", min_length=1, max_length=32)


class TagOut(BaseModel):
    id: int = Field(..., description="Tag id")
    name: str = Field(..., description="Tag name")
    created_at: datetime = Field(..., description="Created timestamp")


class NoteCreateRequest(BaseModel):
    title: str = Field("", description="Note title", max_length=120)
    content: str = Field("", description="Note content")
    tag_ids: List[int] = Field(default_factory=list, description="Tag ids to attach")


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Note title", max_length=120)
    content: Optional[str] = Field(None, description="Note content")
    tag_ids: Optional[List[int]] = Field(None, description="Tag ids to attach")


class NoteTagOut(BaseModel):
    id: int = Field(..., description="Tag id")
    name: str = Field(..., description="Tag name")


class NoteOut(BaseModel):
    id: int = Field(..., description="Note id")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content")
    pinned: bool = Field(..., description="Pinned status")
    favorited: bool = Field(..., description="Favorited status")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    tags: List[NoteTagOut] = Field(default_factory=list, description="Tags attached to note")
