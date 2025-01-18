from fastapi import APIRouter, HTTPException
from app.database import db
from app.schemas.grocery_list import GroceryList
import json

router = APIRouter(prefix="/grocery", tags=["grocery"])

@router.post("/grocery-list", response_model=dict)
async def add_grocery_list(grocery_list: dict):
    try:
        result = await db['grocery_list'].insert_one(grocery_list)
        return {"message": "Grocery list added successfully"}
    except:
        raise HTTPException(status_code=500, detail="Grocery list could not be added")

@router.get("/grocery-list/{week}", response_model=dict)
async def get_grocery_list(week: int):
    grocery_list = await db['grocery_list'].find_one({"week": week})
    if not grocery_list:
        raise HTTPException(status_code=404, detail="Grocery list not found")
    grocery_list["_id"] = str(grocery_list["_id"])  # Convert ObjectId to string
    return {"message": "Success", "data": json.dumps(grocery_list)}