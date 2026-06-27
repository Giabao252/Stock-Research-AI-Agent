from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"FastAPI project is running"} 