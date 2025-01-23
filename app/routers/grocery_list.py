from fastapi import APIRouter, HTTPException, Depends
from app.database import db
from app.utils.jwt import get_current_user
import json

router = APIRouter(prefix="/grocery", tags=["grocery"])


@router.post("/grocery-list", response_model=dict)
async def add_grocery_list(
    grocery_list: dict, current_user: dict = Depends(get_current_user)
):
    try:
        grocery_list["user_id"] = current_user["_id"]
        pipeline = [
            {
                "$group": {
                    "_id": "$user_id",  # Group all documents together
                    "maxWeek": {"$max": "$week"},
                }
            }
        ]
        weeks = db["grocery_list"].aggregate(pipeline)
        latest_week = 0
        async for week in weeks:
            print(week)
            if week["_id"] == current_user["_id"]:
                latest_week = week["maxWeek"]
        latest_week += 1
        print(latest_week)
        grocery_list["week"] = latest_week
        # print(latest_week)
        result = await db["grocery_list"].insert_one(grocery_list)
        return {"message": "Grocery list added successfully"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Grocery list could not be added")


@router.get("/grocery-list/{week}", response_model=dict)
async def get_grocery_list(week: int, current_user: dict = Depends(get_current_user)):
    grocery_list = await db["grocery_list"].find_one(
        {"week": week, "user_id": current_user["_id"]}
    )
    if not grocery_list:
        raise HTTPException(status_code=404, detail="Grocery list not found")
    grocery_list["_id"] = str(grocery_list["_id"])
    grocery_list["user_id"] = str(grocery_list["user_id"])  # Convert ObjectId to string
    return {"message": "Success", "data": json.dumps(grocery_list)}


@router.get("/get_week", response_model=dict)
async def get_week(current_user: dict = Depends(get_current_user)):
    try:
        documents = (
            db["grocery_list"].find({"user_id": current_user["_id"]}).sort({"week": -1})
        )
        weeks = []
        async for doc in documents:
            weeks.append(doc["week"])
        if len(weeks) != 0:
            return {"message": "Success", "data": json.dumps(weeks)}
        else:
            return {"message": "Success", "data": json.dumps(weeks)}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Server error")
