from fastapi import APIRouter, Depends
from app.database import db

router = APIRouter(prefix="/nutrition", tags=["nutrition"])

@router.get("/nutrition")
async def get_nutrition_info(ingredient: str):
    try:
        nutri_info = db['foods'].find_one({"description": ingredient}, {"description": 1, "foodNutrients": 1})
        return {"message": "Success", "data": nutri_info}
    except:
        return {"error": "Invalid ingredient"}