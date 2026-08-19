from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    is_valid_email,
    is_valid_password,
)
from db import create_user, get_user_by_email, count_users, claim_unowned_data
from deps import get_current_user

router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _user_out(user):
    return {"id": user["id"], "email": user["email"]}


@router.post("/signup")
def signup(body: SignupRequest):
    email = body.email.strip()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if not is_valid_password(body.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    is_first_user = count_users() == 0

    user_id = create_user(email, hash_password(body.password))

    if is_first_user:
        # Existing pre-auth data (saved jobs, applications, profile) gets
        # handed to whoever signs up first, so the upgrade to multi-user
        # doesn't orphan anything.
        claim_unowned_data(user_id)

    token = create_access_token(user_id, email.lower())
    return {"token": token, "user": {"id": user_id, "email": email.lower()}}


@router.post("/login")
def login(body: LoginRequest):
    user = get_user_by_email(body.email.strip())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(user["id"], user["email"])
    return {"token": token, "user": _user_out(user)}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return _user_out(current_user)
