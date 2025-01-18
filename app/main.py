from fastapi import FastAPI
from app.routers import auth, user, grocery_list, meals, nutrition

app = FastAPI()
# Include routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(grocery_list.router)
app.include_router(meals.router)
app.include_router(nutrition.router)

# Initialize database connection

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Auth System"}
