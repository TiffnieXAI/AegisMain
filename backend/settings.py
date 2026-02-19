from sqlmodel import create_engine, SQLModel

# dont put your database url here, put it in the .env file (then put it in gitignore)
DATABASE_URL = ""


def get_engine():
    engine = create_engine(DATABASE_URL, echo=True)
    return engine


def create_db_and_tables():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


create_db_and_tables()
