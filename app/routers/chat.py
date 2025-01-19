from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/chat")
async def get_nutrition_info(chat: str):
    return {"message": "Success", "data": chat}