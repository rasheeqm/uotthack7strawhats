from fastapi import APIRouter, Depends, HTTPException
from app.utils.jwt import get_current_user
from app.schemas.user import User
from app.database import db
import json


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    del current_user["_id"]
    return {"message": "Success", "data": json.dumps(current_user)}


@router.post("/update_user/", response_model=dict)
async def update_user(user_data: dict, current_user: dict = Depends(get_current_user)):
    """Update or add user fields."""
    try:
        db["users"].update_one(
            {"username": current_user["username"]}, {"$set": user_data}
        )
    except:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "message": "User data updated successfully",
        "data": current_user["username"],
    }
