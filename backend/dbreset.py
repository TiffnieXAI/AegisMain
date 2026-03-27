from sqlmodel import SQLModel, create_engine
from models.wallet import WalletUser, UserTransaction, UserThreatRecord
from models.session import AuthSession
from models.analysis import ContractRegistryCache, SimulationResult, AIAnalysis
from dbsettings import DATABASE_URL

engine = create_engine(DATABASE_URL)


SQLModel.metadata.drop_all(engine)
SQLModel.metadata.create_all(engine)
