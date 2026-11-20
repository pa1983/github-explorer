from fastapi import FastAPI

app = FastAPI(title="app")


@app.get("/")
def read_root():
    return {"message": "Hello from app"}
