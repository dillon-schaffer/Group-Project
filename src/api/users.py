import bcrypt
import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, status

from src import database as db
from src import schemas
from src.api import auth

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("", response_model=schemas.UserCreated, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate):
    """
    Create a new user account.
    
    The password will be securely hashed before storage.
    """
    password_hash = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with db.engine.begin() as connection:
        existing_user = connection.execute(
            sqlalchemy.text("SELECT user_id FROM users WHERE email = :email"),
            {"email": user.email}
        ).fetchone()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

        user_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO users (name, email, password_hash, created_at)
                VALUES (:name, :email, :password_hash, CURRENT_TIMESTAMP)
                RETURNING user_id
                """
            ),
            {"name": user.name, "email": user.email, "password_hash": password_hash}
        ).scalar_one()

        return schemas.UserCreated(user_id=user_id)
