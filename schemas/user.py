from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    user_id: str
    primary_email: Optional[str] = None
    email_verified: bool = False
    display_name: Optional[str] = None
    profile_completed: bool = False
    is_public_analysis_enabled: bool = False
    status: str = Field(default="active")
    created_at: datetime
    last_active_at: datetime


class UserIdentity(BaseModel):
    identity_type: str
    identity_value: str
    user_id: str
    is_primary: bool = False
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
