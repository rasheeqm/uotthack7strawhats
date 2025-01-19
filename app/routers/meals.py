from fastapi import APIRouter, HTTPException, Depends
from app.database import db
from app.schemas.meals import Meal
from typing import List
from app.utils.jwt import get_current_user
import json

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("/meal", response_model=dict)
async def add_meal(meal: dict, current_user: dict = Depends(get_current_user)):
    try:
        meal["user_id"] = current_user["_id"]
        pipeline = [
            {
                "$group": {
                    "_id": "$user_id",  # Group all documents together
                    "maxWeek": {"$max": "$week"},
                }
            }
        ]
        weeks = db["groceries"].aggregate(pipeline)
        latest_week = 0
        async for week in weeks:
            print(week)
            if week["_id"] == current_user["_id"]:
                latest_week = week["maxWeek"]
        latest_week += 1
        meal["week"] = latest_week
        result = await db["meals"].insert_one(meal)
        return {"message": "Meal added successfully"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Cannot add meal")


@router.get("/meals/{week}", response_model=dict)
async def get_meals_by_week(week: int, current_user: dict = Depends(get_current_user)):
    meals_cursor = db["meals"].find({"week": week, "user_id": current_user["_id"]})
    meals = await meals_cursor.to_list(length=None)
    if not meals:
        raise HTTPException(status_code=404, detail="No meals found for this week")
    for meal in meals:
        meal["_id"] = str(meal["_id"])  # Convert ObjectId to string
        meal["user_id"] = str(meal["user_id"])  # Convert ObjectId to string
    return {"message": "Success", "data": json.dumps(meals)}
