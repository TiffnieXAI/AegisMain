from sqlmodel import Field, SQLModel
import uuid
from datetime import datetime, timezone

class Walletdata(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(default=None)
    address: str = Field(default=None)
    balance: str = Field(default=None)

class Transaction(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(default=None)
    threats_blocked: int = Field(default = None)
    trans_approved: int = Field(default = None)
    trans_pending: int = Field(default = None)      # Added pending transactions
    protect_rate: float = Field(default = None)
    totals_scans: int = Field(default = None)