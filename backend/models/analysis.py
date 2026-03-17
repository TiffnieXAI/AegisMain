from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class ContractRegistryCache(SQLModel, table=True):
    __tablename__ = "contract_registry_cache"
    contract_address: str = Field(primary_key=True, max_length=50)
    is_verified: int
    tregistry_status: int
    last_checked_timestamp: Optional[datetime] = None


class SimulationResult(SQLModel, table=True):
    __tablename__ = "simulation_results"
    simulation_id: Optional[int] = Field(default=None, primary_key=True)
    transaction_hash: str = Field(max_length=100)
    simulation_summary: str = Field(max_length=255)
    # foreign key: transaction_hash references user_transactions.transaction_hash


class AIAnalysis(SQLModel, table=True):
    __tablename__ = "ai_analysis"
    analysis_id: Optional[int] = Field(default=None, primary_key=True)
    transaction_hash: str = Field(max_length=100)
    ai_summary: str = Field(max_length=255)
    recommendation: str = Field(max_length=255)
    trust_score: int
    # foreign key: transaction_hash references user_transactions.transaction_hash
