from fastapi import APIRouter, HTTPException
from app.database import db
import json

router = APIRouter(prefix="/nutrition", tags=["nutrition"])

@router.get("/nutrition")
async def get_nutrition_info(ingredient: str):
    try:
        nutri_info = await db['foods'].find_one({"description": ingredient}, {"description": 1, "foodNutrients": 1, "_id": 0})
        return {"message": "Success", "data": json.dumps(nutri_info)}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Nutritional info not found")