from sqlmodel import SQLModel, Field
import uuid  # not sure if needed pero maganda to generate unique ids for wallets
from datetime import datetime, timezone


class Wallet(SQLModel, table=True):
    id: str = Field(primary_key=True)
