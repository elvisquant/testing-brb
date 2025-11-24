# In app/routers/role.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/roles",
    tags=['Roles API']
)

# --- CREATE a new role (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.RoleOut)
def create_role(
    role_data: schemas.RoleCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new role (e.g., 'driver', 'mechanic'). Requires 'admin' or 'superadmin' role.
    """
    # Check if a role with the same name already exists
    existing_role = db.query(models.Role).filter(models.Role.name == role_data.name.lower()).first()
    if existing_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Role with name '{role_data.name}' already exists.")

    new_role = models.Role(name=role_data.name.lower(), description=role_data.description)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

# --- GET all roles (Any authenticated user) ---
@router.get("/", response_model=List[schemas.RoleOut])
def get_all_roles(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can see the list of available roles.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available roles. Requires any valid logged-in user.
    """
    roles = db.query(models.Role).order_by(models.Role.name).all()
    return roles

# --- GET a specific role by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.RoleOut)
def get_role_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single role.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single role by its ID. Requires any valid logged-in user.
    """
    role = db.query(models.Role).filter(models.Role.id == id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role with id: {id} not found.")
    return role

# --- UPDATE a role by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.RoleOut)
def update_role(
    id: int,
    role_data: schemas.RoleCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a role's details. Requires 'admin' or 'superadmin' role.
    """
    role_query = db.query(models.Role).filter(models.Role.id == id)
    db_role = role_query.first()

    if not db_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role with id: {id} not found")

    # Check for name conflict before updating
    if role_data.name.lower() != db_role.name:
        existing_role = db.query(models.Role).filter(models.Role.name == role_data.name.lower()).first()
        if existing_role:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Role with name '{role_data.name}' already exists.")

    update_data = role_data.model_dump()
    update_data['name'] = update_data['name'].lower() # Ensure name is always lowercase
    role_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(db_role)
    return db_role

# --- DELETE a role by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a role. Requires 'admin' or 'superadmin' role.
    """
    role_query = db.query(models.Role).filter(models.Role.id == id)
    
    if not role_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role with id: {id} not found")
        
    role_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)