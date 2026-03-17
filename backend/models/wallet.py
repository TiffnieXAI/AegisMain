from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class WalletUser(SQLModel, table=True):
    wallet_address: str = Field(primary_key=True, max_length=50)
    created_timestamp: Optional[datetime] = None
    last_login: Optional[datetime] = None


class UserTransaction(SQLModel, table=True):
    transaction_hash: str = Field(primary_key=True, max_length=100)
    wallet_address: str = Field(max_length=50)
    chain_id: str = Field(max_length=20)
    contract_address: str = Field(max_length=50)
    method_called: str = Field(max_length=100)
    timestamp: Optional[datetime] = None
    status: int
    risk_level: int
    # foreign key: wallet_address references wallet_user.wallet_address


class UserThreatRecord(SQLModel, table=True):
    threat_id: Optional[int] = Field(default=None, primary_key=True)
    transaction_hash: str = Field(max_length=100)
    wallet_address: str = Field(max_length=50)
    timestamp: Optional[datetime] = None
    threat_description: str = Field(max_length=255)
    risk_level: int
    # foreign keys:
    #   transaction_hash references user_transactions.transaction_hash
    #   wallet_address references wallet_user.wallet_address
