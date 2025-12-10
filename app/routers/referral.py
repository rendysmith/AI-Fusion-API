from fastapi import APIRouter, Depends, HTTPException, status
from app import schemas  # Теперь это работает корректно
from app.dependencies import get_user_repository
from app.database.repositories.user_repository import UserRepository


router = APIRouter(prefix="/referral", tags=["Referral"])

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: schemas.UserRegisterRequest,
    user_repo: UserRepository = Depends(get_user_repository)
):
    try:
        # Вся логика (хеширование, проверка дублей, начисление баланса) теперь внутри репозитория
        user = await user_repo.register_user(payload)
        return user

    except ValueError as e:
        # Ловим ошибку, если пользователь уже существует (мы бросали ValueError в репозитории)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Любая другая непредвиденная ошибка базы данных
        # Желательно добавить логирование: logging.error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        )