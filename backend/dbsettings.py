from sqlmodel import create_engine, SQLModel, Session

# change to your mysql. We will move this in the future.
DATABASE_URL = "mysql+pymysql://root:lanzsql@localhost/aegisdb"

engine = create_engine(DATABASE_URL, echo=True)

# getter method for session


def get_session():
    with Session(engine) as session:
        yield session
