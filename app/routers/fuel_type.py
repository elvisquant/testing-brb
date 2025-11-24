# In app/routers/fuel_type.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/fuel-types",
    tags=['Fuel Types API']
)

# --- CREATE a new fuel type (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.FuelTypeOut)
def create_fuel_type(
    fuel_type_data: schemas.FuelTypeCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new fuel type (e.g., 'Diesel', 'Gasoline'). Requires 'admin' or 'superadmin' role.
    """
    # Check if a fuel type with the same name already exists (case-insensitive)
    existing_fuel_type = db.query(models.FuelType).filter(
        models.FuelType.fuel_type.ilike(fuel_type_data.fuel_type)
    ).first()
    if existing_fuel_type:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Fuel type '{fuel_type_data.fuel_type}' already exists.")

    new_fuel_type = models.FuelType(**fuel_type_data.model_dump())
    db.add(new_fuel_type)
    db.commit()
    db.refresh(new_fuel_type)
    return new_fuel_type

# --- GET all fuel types (Any authenticated user) ---
@router.get("/", response_model=List[schemas.FuelTypeOut])
def get_all_fuel_types(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of fuel types.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available fuel types. Requires any valid logged-in user.
    """
    fuel_types_list = db.query(models.FuelType).order_by(models.FuelType.fuel_type).all()
    return fuel_types_list

# --- GET a specific fuel type by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.FuelTypeOut)
def get_fuel_type_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single fuel type.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single fuel type by its ID. Requires any valid logged-in user.
    """
    fuel_type = db.query(models.FuelType).filter(models.FuelType.id == id).first()
    if not fuel_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fuel type with id: {id} not found.")
    return fuel_type

# --- UPDATE a fuel type by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.FuelTypeOut)
def update_fuel_type(
    id: int,
    fuel_type_data: schemas.FuelTypeCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a fuel type's details. Requires 'admin' or 'superadmin' role.
    """
    fuel_type_query = db.query(models.FuelType).filter(models.FuelType.id == id)
    db_fuel_type = fuel_type_query.first()

    if not db_fuel_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fuel type with id: {id} not found")

    # Check for name conflict before updating
    if fuel_type_data.fuel_type.lower() != db_fuel_type.fuel_type.lower():
        existing_fuel_type = db.query(models.FuelType).filter(
            models.FuelType.fuel_type.ilike(fuel_type_data.fuel_type)
        ).first()
        if existing_fuel_type:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Fuel type '{fuel_type_data.fuel_type}' already exists.")

    fuel_type_query.update(fuel_type_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_fuel_type)
    return db_fuel_type

# --- DELETE a fuel type by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fuel_type(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a fuel type. Requires 'admin' or 'superadmin' role.
    """
    fuel_type_query = db.query(models.FuelType).filter(models.FuelType.id == id)
    
    if not fuel_type_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fuel type with id: {id} not found")
        
    fuel_type_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)