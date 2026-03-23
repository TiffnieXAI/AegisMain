from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class WalletUser(SQLModel, table=True):
    __tablename__ = "wallet_user"
    wallet_address: str = Field(primary_key=True, max_length=50)
    created_timestamp: Optional[datetime] = None
    last_login: Optional[datetime] = None


class UserTransaction(SQLModel, table=True):
    __tablename__ = "user_transactions"
    transaction_hash: str = Field(primary_key=True, max_length=100)
    wallet_address: str = Field(max_length=50)
    address_destination: str = Field(max_length=50)
    chain_id: str = Field(max_length=20)
    contract_address: str = Field(max_length=50)
    gasUsed: str
    gasCost: str
    method_called: str = Field(max_length=100)
    timestamp: Optional[datetime] = None
    status: int = Field(default=0)
    # status: 0 - pending, 1 - approve, 2 - blocked
    # foreign key: wallet_address references wallet_user.wallet_address


class UserThreatRecord(SQLModel, table=True):
    __tablename__ = "user_threats_record"
    threat_id: Optional[int] = Field(default=None, primary_key=True)
    transaction_hash: str = Field(max_length=100)
    wallet_address: str = Field(max_length=50)
    timestamp: Optional[datetime] = None
    threat_description: str = Field(max_length=255)
    risk_level: int = Field(default=5)
    # risk_level: 0 - safe, 1 - low, 2 - medium, 3 - high, 4 - critical, 5 - unknown 
    # 2-5 risklevel/allblockedtransaction   
    # foreign keys:
    #   transaction_hash references user_transactions.transaction_hash
    #   wallet_address references wallet_user.wallet_address
