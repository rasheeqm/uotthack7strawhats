from fastapi import APIRouter, HTTPException
from app.database import db
import json

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.post("/nutrition")
async def get_nutrition_info(ingredients: dict):
    try:

        print(ingredients)
        nutri_info = db["foods"].find(
            {"description": {"$in": ingredients["name"]}},
            {"description": 1, "foodNutrients": 1, "_id": 0},
        )
        nutritional_info = []
        async for nutri in nutri_info:
            nutritional_info.append(nutri)
        return {"message": "Success", "data": json.dumps(nutritional_info)}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Nutritional info not found")
