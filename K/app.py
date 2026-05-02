import logging
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# إعداد التسجيل (Logging) - سترى هذه السجلات في لوحة تحكم Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Advanced Python Server for Render",
    description="خادم متطور مع عمليات CRUD كاملة، logging، و health check. مُحسَّن لـ Render.",
    version="2.0.0",
)

# إعدادات CORS للسماح بالاتصال من واجهات برمجية أخرى
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في بيئة الإنتاج، حدد origins معينة بدلاً من "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- نماذج البيانات (Schemas) ---
class ItemBase(BaseModel):
    """النموذج الأساسي للعنصر بدون id (يُستخدم عند الإدخال)"""
    name: str = Field(..., min_length=1, max_length=100, example="حاسوب محمول")
    description: Optional[str] = Field(None, max_length=500, example="حاسوب محمول قوي للألعاب")
    price: float = Field(..., gt=0, description="السعر يجب أن يكون أكبر من صفر", example=999.99)

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('اسم العنصر لا يمكن أن يكون فارغًا')
        return v.strip()

class Item(ItemBase):
    """النموذج الكامل للعنصر مع id (يُستخدم في الاستجابة)"""
    id: int = Field(..., example=1)

class ItemUpdate(BaseModel):
    """نموذج لتحديث جزئي للعنصر (كل الحقول اختيارية)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)

# --- قاعدة البيانات الوهمية ---
db: List[Item] = []
# عداد بسيط لتوليد id تلقائيًا
next_id = 1

# --- Middleware لقياس زمن الاستجابة وتسجيله ---
@app.middleware("http")
async def log_and_time_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # تسجيل العملية والمدة الزمنية
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response

# --- نقاط النهاية (Endpoints) ---
@app.get("/", tags=["Root"])
async def read_root():
    """رسالة ترحيبية وفحص سريع للخادم."""
    logger.info("Root endpoint accessed.")
    return {"message": "مرحبًا بك في الخادم المتطور والمستضاف على Render!"}

@app.get("/health", tags=["Health Check"])
async def health_check():
    """نقطة نهاية لفحص صحة الخادم. يستخدمها Render للتأكد من أن الخدمة تعمل."""
    return {"status": "healthy", "db_items_count": len(db)}

# --- عمليات CRUD للعناصر ---
@app.post("/items/", response_model=Item, status_code=status.HTTP_201_CREATED, tags=["Items"])
async def create_item(item_data: ItemBase):
    """
    إنشاء عنصر جديد. يتم توليد id تلقائيًا.
    """
    global next_id
    logger.info(f"محاولة إنشاء عنصر جديد: {item_data.name}")
    
    new_item = Item(id=next_id, **item_data.dict())
    db.append(new_item)
    
    next_id += 1
    logger.info(f"تم إنشاء العنصر بنجاح بمعرف: {new_item.id}")
    return new_item

@app.get("/items/", response_model=List[Item], tags=["Items"])
async def get_items(skip: int = 0, limit: int = 100):
    """
    جلب قائمة بالعناصر مع إمكانية التقسيم (pagination).
    - **skip**: عدد العناصر لتخطيها.
    - **limit**: أقصى عدد للعناصر المُرجعة.
    """
    logger.info(f"جلب العناصر: skip={skip}, limit={limit}")
    return db[skip : skip + limit]

@app.get("/items/{item_id}", response_model=Item, tags=["Items"])
async def get_item(item_id: int):
    """
    جلب عنصر واحد بواسطة id الخاص به.
    """
    logger.info(f"محاولة جلب العنصر بمعرف: {item_id}")
    item = next((item for item in db if item.id == item_id), None)
    if not item:
        logger.warning(f"العنصر بمعرف {item_id} غير موجود.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="العنصر غير موجود")
    return item

@app.put("/items/{item_id}", response_model=Item, tags=["Items"])
async def update_item(item_id: int, item_update: ItemUpdate):
    """
    تحديث عنصر موجود بالكامل (أو جزئيًا). 
    فقط الحقول المُرسلة سيتم تحديثها.
    """
    logger.info(f"محاولة تحديث العنصر بمعرف: {item_id}")
    item_index = next((index for index, item in enumerate(db) if item.id == item_id), None)
    
    if item_index is None:
        logger.warning(f"العنصر بمعرف {item_id} غير موجود للتحديث.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="العنصر غير موجود")

    # استخراج البيانات الحالية
    stored_item = db[item_index]
    # إنشاء قاموس بالبيانات المحدثة (مع استبعاد القيم غير المُرسلة)
    update_data = item_update.dict(exclude_unset=True)
    # تحديث النموذج الموجود
    updated_item = stored_item.copy(update=update_data)
    db[item_index] = updated_item
    
    logger.info(f"تم تحديث العنصر بمعرف: {item_id} بنجاح")
    return updated_item

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Items"])
async def delete_item(item_id: int):
    """
    حذف عنصر بواسطة id الخاص به.
    """
    logger.info(f"محاولة حذف العنصر بمعرف: {item_id}")
    item_index = next((index for index, item in enumerate(db) if item.id == item_id), None)
    
    if item_index is None:
        logger.warning(f"العنصر بمعرف {item_id} غير موجود للحذف.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="العنصر غير موجود")

    deleted_item = db.pop(item_index)
    logger.info(f"تم حذف العنصر: {deleted_item.name} (id={item_id})")
    # لا نُرجع محتوى، فقط نؤكد النجاح بكود 204
    return None