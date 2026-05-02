from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import time

app = FastAPI(
    title="Advanced Python Server",
    description="خادم متطور مستضاف على Render",
    version="1.0.0"
)

# إعدادات CORS للسماح بالاتصال من واجهات برمجية أخرى
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# نموذج بيانات (Schema) باستخدام Pydantic
class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float

# قاعدة بيانات وهمية في الذاكرة
db = []

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to my advanced server on Render!"}

@app.post("/items/", response_model=Item, tags=["Items"])
def create_item(item: Item):
    db.append(item)
    return item

@app.get("/items/", response_model=List[Item], tags=["Items"])
def get_items():
    return db