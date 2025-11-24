# In app/routers/vehicle_make.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/vehicle-makes",
    tags=['Vehicle Makes API']
)

# --- CREATE a new vehicle make (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.VehicleMakeOut)
def create_vehicle_make(
    make_data: schemas.VehicleMakeCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new vehicle make (e.g., 'Toyota', 'Ford'). Requires 'admin' or 'superadmin' role.
    """
    # Check if a make with the same name already exists (case-insensitive)
    existing_make = db.query(models.VehicleMake).filter(
        models.VehicleMake.vehicle_make.ilike(make_data.vehicle_make)
    ).first()
    if existing_make:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle make '{make_data.vehicle_make}' already exists.")

    new_make = models.VehicleMake(**make_data.model_dump())
    db.add(new_make)
    db.commit()
    db.refresh(new_make)
    return new_make

# --- GET all vehicle makes (Any authenticated user) ---
@router.get("/", response_model=List[schemas.VehicleMakeOut])
def get_all_vehicle_makes(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of makes.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available vehicle makes. Requires any valid logged-in user.
    """
    makes = db.query(models.VehicleMake).order_by(models.VehicleMake.vehicle_make).all()
    return makes

# --- GET a specific vehicle make by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.VehicleMakeOut)
def get_vehicle_make_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: The original file had a typo here. This is the correct way.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single vehicle make by its ID. Requires any valid logged-in user.
    """
    make = db.query(models.VehicleMake).filter(models.VehicleMake.id == id).first()
    if not make:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle make with id: {id} not found.")
    return make

# --- UPDATE a vehicle make by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.VehicleMakeOut)
def update_vehicle_make(
    id: int,
    make_data: schemas.VehicleMakeCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a vehicle make's details. Requires 'admin' or 'superadmin' role.
    """
    make_query = db.query(models.VehicleMake).filter(models.VehicleMake.id == id)
    db_make = make_query.first()

    if not db_make:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle make with id: {id} not found")

    # Check for name conflict before updating
    if make_data.vehicle_make.lower() != db_make.vehicle_make.lower():
        existing_make = db.query(models.VehicleMake).filter(
            models.VehicleMake.vehicle_make.ilike(make_data.vehicle_make)
        ).first()
        if existing_make:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle make '{make_data.vehicle_make}' already exists.")

    make_query.update(make_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_make)
    return db_make

# --- DELETE a vehicle make by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_make(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a vehicle make. Requires 'admin' or 'superadmin' role.
    """
    make_query = db.query(models.VehicleMake).filter(models.VehicleMake.id == id)
    
    if not make_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle make with id: {id} not found")
        
    make_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)