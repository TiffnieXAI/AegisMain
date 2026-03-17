from sqlmodel import create_engine, SQLModel

DATABASE_URL = "mysql+pymysql://root:admin123@localhost/aegis"

engine = create_engine(DATABASE_URL, echo=True)
