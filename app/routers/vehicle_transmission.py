# In app/routers/vehicle_transmission.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/vehicle-transmissions",
    tags=['Vehicle Transmissions API']
)

# --- CREATE a new vehicle transmission type (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.VehicleTransmissionOut)
def create_vehicle_transmission(
    transmission_data: schemas.VehicleTransmissionCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new vehicle transmission type (e.g., 'Automatic', 'Manual'). Requires 'admin' or 'superadmin' role.
    """
    # Check if a transmission with the same name already exists (case-insensitive)
    existing_transmission = db.query(models.VehicleTransmission).filter(
        models.VehicleTransmission.vehicle_transmission.ilike(transmission_data.vehicle_transmission)
    ).first()
    if existing_transmission:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle transmission type '{transmission_data.vehicle_transmission}' already exists.")

    new_transmission = models.VehicleTransmission(**transmission_data.model_dump())
    db.add(new_transmission)
    db.commit()
    db.refresh(new_transmission)
    return new_transmission

# --- GET all vehicle transmission types (Any authenticated user) ---
@router.get("/", response_model=List[schemas.VehicleTransmissionOut])
def get_all_vehicle_transmissions(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of transmission types.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available vehicle transmission types. Requires any valid logged-in user.
    """
    transmissions_list = db.query(models.VehicleTransmission).order_by(models.VehicleTransmission.vehicle_transmission).all()
    return transmissions_list

# --- GET a specific vehicle transmission type by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.VehicleTransmissionOut)
def get_vehicle_transmission_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single transmission type.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single vehicle transmission type by its ID. Requires any valid logged-in user.
    """
    transmission = db.query(models.VehicleTransmission).filter(models.VehicleTransmission.id == id).first()
    if not transmission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle transmission type with id: {id} not found.")
    return transmission

# --- UPDATE a vehicle transmission type by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.VehicleTransmissionOut)
def update_vehicle_transmission(
    id: int,
    transmission_data: schemas.VehicleTransmissionCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a vehicle transmission type's details. Requires 'admin' or 'superadmin' role.
    """
    transmission_query = db.query(models.VehicleTransmission).filter(models.VehicleTransmission.id == id)
    db_transmission = transmission_query.first()

    if not db_transmission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle transmission type with id: {id} not found")

    # Check for name conflict before updating
    if transmission_data.vehicle_transmission.lower() != db_transmission.vehicle_transmission.lower():
        existing_transmission = db.query(models.VehicleTransmission).filter(
            models.VehicleTransmission.vehicle_transmission.ilike(transmission_data.vehicle_transmission)
        ).first()
        if existing_transmission:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle transmission type '{transmission_data.vehicle_transmission}' already exists.")

    transmission_query.update(transmission_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_transmission)
    return db_transmission

# --- DELETE a vehicle transmission type by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_transmission(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a vehicle transmission type. Requires 'admin' or 'superadmin' role.
    """
    transmission_query = db.query(models.VehicleTransmission).filter(models.VehicleTransmission.id == id)
    
    if not transmission_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle transmission type with id: {id} not found")
        
    transmission_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)