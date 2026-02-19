from fastapi import FastAPI
from typing import Optional
# para sa mga python na mababa version lang


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}
