from pydantic import BaseModel, Field
from typing import Literal, List


class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^\S+@\S+\.\S+$")
    password: str = Field(..., min_length=6)
    age: int = Field(..., ge=12, le=110)
    sex: Literal[
        "Male",
        "Female",
        "Non-Binary",
        "Transgender",
        "Cisgender",
        "Heterosexual",
        "Homosexual",
        "Bisexual",
        "Asexual",
        "Pansexual",
    ] = Field()
    height: int = Field(...)
    weight: int = Field(...)
    diet_preference: List[
        Literal[
            "Omnivore",
            "Vegetarian",
            "Vegan",
            "Gluten-Free",
            "Halal",
            "Kosher",
        ]
    ] = Field(...)
    allergies: List[
        Literal[
            "Peanut",
            "Tree Nut",
            "Milk",
            "Egg",
            "Wheat",
            "Soy",
            "Fish",
            "Shellfish",
            "Gluten",
            "Pollen",
            "Dust",
            "Mold",
            "Pet Dander",
            "Insect Stings",
            "Latex",
            "Penicillin",
            "Sulfa Drugs",
        ]
    ] = Field(...)
    activity_level: Literal[
        "Sedentary",
        "Lightly Active",
        "Moderately Active",
        "Very Active",
        "Extremely Active",
    ] = Field(...)
    goal: Literal[
        "Weight Loss",
        "Muscle Gain",
        "Both",
    ] = Field(...)
    medical_conditions: Literal[
        "Celiac Disease", "Diabetes", "Hypertension", "Cholesterol", "Obesity"
    ] = Field(...)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
