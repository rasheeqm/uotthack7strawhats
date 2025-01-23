from typing import List
from pydantic import BaseModel, Field
from bson import ObjectId


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


class Ingredient(BaseModel):
    ingredient_name: str = Field(..., description="Name of the ingredient")
    quantity: float = Field(..., description="Quantity of the ingredient")


class NutritionalInfo(BaseModel):
    macro: str = Field(
        ..., description="Name of the macro nutrient (e.g., protein, carbs, fats)"
    )
    quantity: str = Field(..., description="Quantity of the macro nutrient in grams")


class Meal(BaseModel):
    user_id: PyObjectId = Field(
        ..., description="Reference to the user's _id in the users collection"
    )
    week: int = Field(..., ge=1, le=52, description="Week number (1-52)")
    meal_name: str = Field(..., description="Name of the meal")
    ingredients: List[Ingredient] = Field(
        ..., description="List of ingredients with quantities"
    )
    nutritional_info: List[NutritionalInfo] = Field(
        ..., description="Nutritional information of the meal"
    )
    recipe: str = Field(...)

    class Config:
        # Enable JSON encoding of ObjectId
        json_encoders = {ObjectId: str}
