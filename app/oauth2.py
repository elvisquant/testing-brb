# In app/oauth2.py

from jose import jwt
from jwt.exceptions import PyJWTError # FIXED: Changed JWTError to PyJWTError
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, status, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from . import schemas, database, models
from .config import settings

# --- SECTION 1: CORE CONFIGURATION AND TOKEN FUNCTIONS ---

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str, credentials_exception: HTTPException) -> schemas.TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = schemas.TokenData.model_validate(payload)
    except PyJWTError: # FIXED: Changed JWTError to PyJWTError
        raise credentials_exception
    return token_data

# --- SECTION 2: DEPENDENCIES FOR API ROUTERS (using Authorization Header) ---

# This is changed to allow our unified function to work correctly.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/", auto_error=False)

def get_current_user_from_header(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.User:
    """Primary dependency for API endpoints that strictly require a header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"},
    )
    if not token: # Explicit check because auto_error is False now
        raise credentials_exception
    token_data = verify_access_token(token, credentials_exception)
    user = db.query(models.User).filter(models.User.id == token_data.user_id).first()
    if user is None or user.status != "active":
        raise credentials_exception
    return user

def require_role_for_api(allowed_roles: List[str]):
    """A dependency factory for securing API endpoints via header."""
    def role_checker(user: models.User = Depends(get_current_user_from_header)):
        user_role = user.role.name.lower() if user.role and user.role.name else ""
        if user_role not in [role.lower() for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Action requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker

# --- Specific API Dependencies (Kept for backward compatibility) ---
require_admin_role_for_api = require_role_for_api(["admin", "superadmin"])
# ... (and your other specific role dependencies)


# --- SECTION 3: DEPENDENCIES FOR HTML PAGE LOADS (using Secure Cookie) ---

def get_current_user_from_cookie(request: Request, db: Session = Depends(database.get_db)) -> models.User:
    """Primary dependency for HTML pages. Reads token from cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": "/login.html"}
    )
    token = request.cookies.get("access_token")
    if token is None:
        raise credentials_exception
    
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    token_data = verify_access_token(token, credentials_exception)
    user = db.query(models.User).filter(models.User.id == token_data.user_id).first()
    if user is None or user.status != "active":
        raise credentials_exception
    return user

def require_role_for_page(allowed_roles: List[str]):
    """A dependency factory for securing HTML pages."""
    def role_checker(user: models.User = Depends(get_current_user_from_cookie)):
        user_role = user.role.name.lower() if user.role and user.role.name else ""
        if user_role not in [role.lower() for role in allowed_roles]:
            raise HTTPException(status_code=403, detail="You do not have permission to view this page.")
        return user
    return role_checker

# --- RE-ADDED: Specific Page Dependencies (for cleaner code in main.py) ---
require_admin_page = require_role_for_page(["admin", "superadmin"])
require_user_page = require_role_for_page(["user"]) # This was the missing function
require_driver_page = require_role_for_page(["driver"])
require_chef_page = require_role_for_page(["chef"])
require_logistic_page = require_role_for_page(["logistic"])
require_charoi_page = require_role_for_page(["charoi"])


# --- NEW SECTION 4: UNIFIED DEPENDENCIES FOR FLEXIBLE API ENDPOINTS ---

def get_current_active_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme), # Tries header first
    db: Session = Depends(database.get_db)
) -> models.User:
    """A flexible dependency that gets the user from a header OR a cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials, please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    auth_token = token
    if not auth_token:
        cookie_token = request.cookies.get("access_token")
        if cookie_token and cookie_token.startswith("Bearer "):
            auth_token = cookie_token.split(" ")[1]

    if not auth_token:
        raise credentials_exception
        
    token_data = verify_access_token(auth_token, credentials_exception)
    user = db.query(models.User).options(joinedload(models.User.role)).filter(models.User.id == token_data.user_id).first()

    if user is None or user.status != "active":
        raise credentials_exception
        
        
    return user

def require_role(allowed_roles: List[str]):
    """A flexible dependency factory for APIs, using the unified user retrieval."""
    def role_checker(user: models.User = Depends(get_current_active_user)):
        user_role = user.role.name.lower() if user.role and user.role.name else ""
        if user_role not in [role.lower() for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. User does not have the required permissions."
            )
        return user
    return role_checker