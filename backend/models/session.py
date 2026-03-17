from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_session"
    session_id: Optional[int] = Field(default=None, primary_key=True)
    wallet_address: str = Field(max_length=50)
    nonce: str = Field(max_length=100)
    signature: str = Field(default="", max_length=200)
    created_timestamp: Optional[datetime] = None
    # foreign key: wallet_address references wallet_user.wallet_address
