from fastapi import APIRouter, HTTPException
from app.database import db
from app.schemas.meals import Meal
from typing import List
import json

router = APIRouter(prefix="/meals", tags=["meals"])

@router.post("/meal", response_model=dict)
async def add_meal(meal: dict):
    try:
        result = await db['meals'].insert_one(meal)
        return {"message": "Meal added successfully"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Cannot add meal")

@router.get("/meals/{week}", response_model=dict)
async def get_meals_by_week(week: int):
    meals_cursor = db['meals'].find({"week": week})
    meals = await meals_cursor.to_list(length=None)
    if not meals:
        raise HTTPException(status_code=404, detail="No meals found for this week")
    for meal in meals:
        meal["_id"] = str(meal["_id"])  # Convert ObjectId to string
    return {"message": "Success", "data": json.dumps(meals)}