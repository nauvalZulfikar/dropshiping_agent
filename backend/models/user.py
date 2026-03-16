from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class UserProfile(BaseModel):
    id: UUID
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
