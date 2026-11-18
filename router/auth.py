import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Users
from Pydantic.create_user import CreateUsers
# from router.Emailverify import sendEmail
# from Verify.otp import generateOtp
# from Verify.verify_access_token import generate_token

load_dotenv()

router = APIRouter()

# Put SECRET_KEY in your .env file, never in the source code
SECRET_KEY = "iQNQj2ctmVdMbbf/Fu6BLD9y7aGnwHHivHGkdnpti5g="
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Add it to your .env file.")

ALGORITHM = "HS256"

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="login")
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()





def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("id")
        role = payload.get("role")

        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")

        return {"username": username, "id": user_id, "role": role}

    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


user_dependency = Annotated[dict, Depends(get_current_user)]


def authenticate_user(username: str, password: str, db: Session):
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        return False

    if bcrypt_context.verify(password, user.password_hash):
        return user
    return False


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    payload = {
        "sub": username,
        "id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/createUser")
def create_user(db: db_dependency, newuser: CreateUsers):
    if db.query(Users).filter(Users.username == newuser.username).first():
        raise HTTPException(status_code=409, detail="User Already Exists")

    if db.query(Users).filter(Users.email == newuser.email).first():
        raise HTTPException(status_code=409, detail="Email Already Exists")

    user_model = Users(
        username=newuser.username,
        email=newuser.email,
        password_hash=bcrypt_context.hash(newuser.password),
        is_active =True,
        is_verified = True
    )
    db.add(user_model)

    db.commit()

 
db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict,Depends(get_current_user)]

@router.post("/login")
def user_login(
    db: db_dependency,
    formdata: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = authenticate_user(formdata.username, formdata.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # Once your OTP verify endpoint exists, add:
    # if not user.is_verified:
    #     raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token(user.username, user.id, user.role, timedelta(days=1))
    return {
        "access_token": token,
        "token_type": "bearer",
    }
