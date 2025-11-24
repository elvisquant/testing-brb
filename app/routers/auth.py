# In app/routers/auth.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import Annotated

from .. import database, schemas, models, utils, oauth2 

router = APIRouter(
    prefix="/login", 
    tags=['Authentication']
)

# This endpoint now accepts a `Response` object to set the cookie
@router.post("/", response_model=schemas.Token)
def login(
    response: Response, # FastAPI will inject the response object here
    user_credentials: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(database.get_db)
):
    """
    Handles user login and, upon success, sets a secure HttpOnly cookie
    for session management while also returning the standard token response.
    """
    identifier = user_credentials.username 
    password = user_credentials.password

    db_user = (
        db.query(models.User)
        .options(joinedload(models.User.role), joinedload(models.User.service))
        .filter(or_(models.User.email == identifier, models.User.matricule == identifier))
        .first()
    )

    if not db_user or not utils.verify(password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect matricule, email, or password"
        )

    if db_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account access denied. Your account status is '{db_user.status}'."
        )
    
    if not db_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no role assigned. Cannot log in."
        )

    token_payload_data = {
        "sub": db_user.email, "user_id": db_user.id,      
        "status": db_user.status, "role": db_user.role.name
    }
    
    access_token = oauth2.create_access_token(data=token_payload_data) 
    
    # --- CRITICAL CHANGE: SET THE COOKIE ---
    # This cookie will be automatically sent by the browser on all subsequent requests.
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # Makes it inaccessible to JavaScript (more secure)
        samesite="lax", # Good for security
        secure=False,   # IMPORTANT: Set to True when you deploy with HTTPS
        path="/"        # Available to the entire site
    )
    # ----------------------------------------
    
    # Return the same JSON response as before for your frontend script
    return {
        "access_token": access_token, "token_type": "bearer",
        "user_id": db_user.id, "username": db_user.email,
        "status": db_user.status, "role": db_user.role.name,
        "service_id": db_user.service_id
    }

