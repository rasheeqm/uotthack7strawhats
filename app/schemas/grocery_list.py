from typing import List
from pydantic import BaseModel, Field
from bson import ObjectId


# Custom Pydantic type for ObjectId
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class GroceryItem(BaseModel):
    ingredient_name: str = Field(..., description="Name of the ingredient")
    quantity: str = Field(..., description="Quantity of the ingredient")
    price: float = Field(..., description="Price of the ingredient")


class GroceryList(BaseModel):
    user_id: PyObjectId = Field(
        ..., description="Reference to the user's _id in the users collection"
    )
    week: int = Field(..., ge=1, le=52, description="Week number (1-52)")
    groceries: List[GroceryItem] = Field(..., description="List of grocery items")

    class Config:
        # Enable JSON encoding of ObjectId
        json_encoders = {ObjectId: str}
