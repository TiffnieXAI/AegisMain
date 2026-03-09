from sqlmodel import create_engine, SQLModel
from AegisMain.backend.models.wallet import Walletdata
DATABASE_URL = "mysql+pymysql://root:admin123@localhost/aegis"

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

create_db_and_tables()