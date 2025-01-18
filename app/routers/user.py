from fastapi import APIRouter, Depends
from app.utils.jwt import get_current_user
from app.schemas.user import User
from app.database import db

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "email": current_user["email"]}

@router.post("/update_user/", response_model=User)
async def update_user(user_data, current_user: dict = Depends(get_current_user)):
    """ Update or add user fields. """
    try: 
        db['users'].update_one({"username": current_user['username']}, {"$set": user_data})
    except:
        return {"error": "Error while updating user data"}
    return {"message": "User data updated successfully", "user_data": current_user['username']}