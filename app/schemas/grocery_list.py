from typing import List
from pydantic import BaseModel, Field

class GroceryItem(BaseModel):
    ingredient_name: str = Field(..., description="Name of the ingredient")
    quantity: str = Field(..., description="Quantity of the ingredient")
    price: float = Field(..., description="Price of the ingredient")

class GroceryList(BaseModel):
    week: int = Field(..., ge=1, le=52, description="Week number (1-52)")
    groceries: List[GroceryItem] = Field(..., description="List of grocery items")