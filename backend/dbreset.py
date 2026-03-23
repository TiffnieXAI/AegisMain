from sqlmodel import SQLModel, create_engine
from models.wallet import WalletUser, UserTransaction, UserThreatRecord
from models.session import AuthSession
from models.analysis import ContractRegistryCache, SimulationResult, AIAnalysis

engine = create_engine("mysql+pymysql://root:admin123@localhost/aegis")


SQLModel.metadata.drop_all(engine)
SQLModel.metadata.create_all(engine)