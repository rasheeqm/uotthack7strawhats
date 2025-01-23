from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.utils.security import authenticate_user, get_password_hash
from app.utils.jwt import create_access_token
from app.database import db
from app.schemas.user import Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: dict):
    existing_user = await db["users"].find_one({"username": user["username"]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )
    user_data = {
        "username": user["username"],
        "email": user["email"],
        "password": get_password_hash(user["password"]),
        "age": user["age"],
        "sex": user["sex"],
        "height": user["height"],
        "weight": user["weight"],
        "diet_preference": user["diet_preference"],
        "allergies": user["allergies"],
        "activity_level": user["activity_level"],
        "goal": user["goal"],
        "medical_conditions": user["medical_conditions"],
    }
    await db["users"].insert_one(user_data)
    return {"message": "User registered successfully"}


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
