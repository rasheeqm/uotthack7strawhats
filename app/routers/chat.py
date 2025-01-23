from fastapi import APIRouter, Depends
from Agents.master_agent import run_grocery_workflow
from app.utils.jwt import get_current_user
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/reply", response_model=dict)
async def get_nutrition_info(
    chat: dict,
    current_user: dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    try:
        reply = run_grocery_workflow(current_user, token, chat["message"])
        if reply:
            return {"message": "Success", "reply": reply}
    except Exception as e:
        print(e)
        return {"message": "Fail"}
