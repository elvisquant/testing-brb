# In app/routers/user.py

from fastapi import APIRouter, Depends, status, HTTPException, Response, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional

from .. import models, schemas, oauth2, utils
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/users",
    tags=['Users API']
)


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(oauth2.get_current_active_user)):
    """
    Returns the details of the currently authenticated user by reading
    the secure HttpOnly cookie. This is the primary endpoint for dashboards
    to identify the logged-in user.
    """
    return current_user


# --- CREATE a new user (Public Endpoint) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
def create_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new user with a default role of "user".
    This is a public endpoint for the signup form.
    """
    existing_user = db.query(models.User).filter(
        or_(
            models.User.matricule == user_data.matricule,
            models.User.email == user_data.email,
            models.User.telephone == user_data.telephone
        )
    ).first()

    if existing_user:
        if existing_user.matricule == user_data.matricule:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Matricule already exists")
        if existing_user.email == user_data.email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        if existing_user.telephone == user_data.telephone:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Telephone number already in use")

    default_role = db.query(models.Role).filter(models.Role.name == "user").first()
    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default 'user' role not found. Please ensure it exists in the 'roles' table."
        )

    hashed_password = utils.hash(user_data.password)
    user_data_dict = user_data.model_dump()
    user_data_dict["password"] = hashed_password
    user_data_dict["role_id"] = default_role.id
    
    new_user = models.User(**user_data_dict)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# --- GET all users (with role-based access) ---
@router.get("/", response_model=List[schemas.UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_role_for_api(["admin", "superadmin", "charoi", "logistic", "chef"])),
    limit: int = 100,
    skip: int = 0,
    search: Optional[str] = "",
    role: Optional[str] = None
):
    """
    Get a list of users.
    - Admins/Superadmins can see all users.
    - Charoi/Logistics/Chefs can only use this endpoint to get a list of drivers.
    """
    user_role = current_user.role.name.lower() if current_user.role else ""
    is_admin = user_role in ["admin", "superadmin"]

    if not is_admin and role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this list of users."
        )

    query = db.query(models.User).options(joinedload(models.User.role))
    
    if role:
        # <<<--- FIX: ALSO FILTER FOR ACTIVE STATUS WHEN GETTING DRIVERS
        query = query.join(models.Role).filter(
            models.Role.name == role.lower(),
            models.User.status == 'active'  # Only include active drivers
        )

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.User.matricule.ilike(search_term),
                models.User.first_name.ilike(search_term),
                models.User.last_name.ilike(search_term),
                models.User.email.ilike(search_term)
            )
        )
    
    users = query.order_by(models.User.id).limit(limit).offset(skip).all()
    return users


# --- GET a specific user by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.UserOut)
def get_user_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single user by their ID. Requires any valid logged-in user.
    """
    user = db.query(models.User).options(joinedload(models.User.role)).filter(models.User.id == id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id: {id} was not found."
        )
    return user


# --- GET all users by role name (Admin only) ---
@router.get("/by_role/{role_name}", response_model=List[schemas.UserOut])
def get_users_by_role(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Get all users who have a specific role (e.g., "driver"). Requires admin role.
    """
    users = db.query(models.User).join(models.Role).filter(models.Role.name == role_name.lower()).options(joinedload(models.User.role)).all()
    
    return users


# --- UPDATE a user by ID (Admin or the user themselves) ---
@router.put("/{id}", response_model=schemas.UserOut)
def update_user(
    id: int,
    user_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Update a user's details. An admin can update anyone.
    A regular user can only update their own details.
    """
    user_query = db.query(models.User).filter(models.User.id == id)
    db_user = user_query.first()

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id: {id} not found")

    is_admin = current_user.role.name in ["admin", "superadmin"]
    is_updating_self = current_user.id == db_user.id

    if not is_admin and not is_updating_self:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    update_data = user_data.model_dump(exclude_unset=True)

    if not is_admin:
        if "role_id" in update_data or "status" in update_data:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to change role or status")

    if "role_id" in update_data and update_data["role_id"] is not None:
        role = db.query(models.Role).filter(models.Role.id == update_data["role_id"]).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role with ID {update_data['role_id']} not found")

    user_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(db_user)
    
    return db_user


# --- DELETE a user by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a user. Requires 'admin' or 'superadmin' role.
    """
    user_query = db.query(models.User).filter(models.User.id == id)
    
    if not user_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id: {id} not found")
        
    user_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)