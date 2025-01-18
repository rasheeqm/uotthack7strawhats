from fastapi import FastAPI
from app.routers import auth, user

app = FastAPI()
# Include routers
app.include_router(auth.router)
app.include_router(user.router)

# Initialize database connection

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Auth System"}
