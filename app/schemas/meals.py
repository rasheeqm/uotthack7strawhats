from typing import List
from pydantic import BaseModel, Field

class Ingredient(BaseModel):
    ingredient_name: str = Field(..., description="Name of the ingredient")
    quantity: float = Field(..., description="Quantity of the ingredient")

class NutritionalInfo(BaseModel):
    macro: str = Field(..., description="Name of the macro nutrient (e.g., protein, carbs, fats)")
    quantity: str = Field(..., description="Quantity of the macro nutrient in grams")

class Meal(BaseModel):
    week: int = Field(..., ge=1, le=52, description="Week number (1-52)")
    meal_name: str = Field(..., description="Name of the meal")
    ingredients: List[Ingredient] = Field(..., description="List of ingredients with quantities")
    nutritional_info: List[NutritionalInfo] = Field(..., description="Nutritional information of the meal")