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
    allergies: str = Field(...)
    activity_level: Literal[
        "Sedentary",
        "Lightly Active",
        "Moderately Active",
        "Very Active",
        "Extremely Active",
    ] = Field(...)
    goal: Literal["Weight Loss", "Muscle Gain", "Both", "Stay fit"] = Field(...)
    medical_conditions: str = Field(...)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
