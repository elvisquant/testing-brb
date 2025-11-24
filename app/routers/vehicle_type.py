# In app/routers/vehicle_type.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/vehicle-types",
    tags=['Vehicle Types API']
)

# --- CREATE a new vehicle type (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.VehicleTypeOut)
def create_vehicle_type(
    type_data: schemas.VehicleTypeCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new vehicle type (e.g., 'Sedan', 'SUV', 'Truck'). Requires 'admin' or 'superadmin' role.
    """
    # Check if a type with the same name already exists (case-insensitive)
    existing_type = db.query(models.VehicleType).filter(
        models.VehicleType.vehicle_type.ilike(type_data.vehicle_type)
    ).first()
    if existing_type:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle type '{type_data.vehicle_type}' already exists.")

    new_type = models.VehicleType(**type_data.model_dump())
    db.add(new_type)
    db.commit()
    db.refresh(new_type)
    return new_type

# --- GET all vehicle types (Any authenticated user) ---
@router.get("/", response_model=List[schemas.VehicleTypeOut])
def get_all_vehicle_types(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of types.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available vehicle types. Requires any valid logged-in user.
    """
    types_list = db.query(models.VehicleType).order_by(models.VehicleType.vehicle_type).all()
    return types_list

# --- GET a specific vehicle type by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.VehicleTypeOut)
def get_vehicle_type_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single type.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single vehicle type by its ID. Requires any valid logged-in user.
    """
    veh_type = db.query(models.VehicleType).filter(models.VehicleType.id == id).first()
    if not veh_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle type with id: {id} not found.")
    return veh_type

# --- UPDATE a vehicle type by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.VehicleTypeOut)
def update_vehicle_type(
    id: int,
    type_data: schemas.VehicleTypeCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a vehicle type's details. Requires 'admin' or 'superadmin' role.
    """
    type_query = db.query(models.VehicleType).filter(models.VehicleType.id == id)
    db_type = type_query.first()

    if not db_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle type with id: {id} not found")

    # Check for name conflict before updating
    if type_data.vehicle_type.lower() != db_type.vehicle_type.lower():
        existing_type = db.query(models.VehicleType).filter(
            models.VehicleType.vehicle_type.ilike(type_data.vehicle_type)
        ).first()
        if existing_type:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle type '{type_data.vehicle_type}' already exists.")

    type_query.update(type_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_type)
    return db_type

# --- DELETE a vehicle type by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_type(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a vehicle type. Requires 'admin' or 'superadmin' role.
    """
    type_query = db.query(models.VehicleType).filter(models.VehicleType.id == id)
    
    if not type_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle type with id: {id} not found")
        
    type_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)