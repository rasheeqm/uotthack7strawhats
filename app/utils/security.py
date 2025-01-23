from passlib.context import CryptContext
from app.database import db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(username: str, password: str):
    user = await db["users"].find_one({"username": username})
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    return user
