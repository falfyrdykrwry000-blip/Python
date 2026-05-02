from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from Render 🚀"}

@app.get("/ping")
def ping():
    return {"status": "ok"}