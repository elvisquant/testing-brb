# In app/routers/vehicle.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/vehicles",
    tags=['Vehicles API']
)

# --- CREATE a new vehicle (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.VehicleOut)
def create_vehicle(
    vehicle_data: schemas.VehicleCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new vehicle in the fleet. Requires 'admin' or 'superadmin' role.
    """
    # Check if a vehicle with the same plate number or VIN already exists
    existing_vehicle = db.query(models.Vehicle).filter(
        (models.Vehicle.plate_number == vehicle_data.plate_number) | (models.Vehicle.vin == vehicle_data.vin)
    ).first()
    if existing_vehicle:
        if existing_vehicle.plate_number == vehicle_data.plate_number:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle with plate number '{vehicle_data.plate_number}' already exists.")
        if existing_vehicle.vin == vehicle_data.vin:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle with VIN '{vehicle_data.vin}' already exists.")

    new_vehicle = models.Vehicle(**vehicle_data.model_dump())
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle

# --- GET all vehicles (Any authenticated user) ---
@router.get("/", response_model=List[schemas.VehicleOut])
def get_all_vehicles(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of vehicles.
    current_user: models.User = Depends(oauth2.get_current_user_from_header),
    limit: int = 100,
    skip: int = 0,
    search: Optional[str] = ""
):
    """
    Get a list of all vehicles in the fleet. Requires any valid logged-in user.
    """
    query = db.query(models.Vehicle)
    if search:
        search_term = f"%{search}%"
        query = query.filter(models.Vehicle.plate_number.ilike(search_term))
        
    vehicles = query.order_by(models.Vehicle.id).limit(limit).offset(skip).all()
    return vehicles

# --- GET a specific vehicle by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.VehicleOut)
def get_vehicle_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single vehicle.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single vehicle by its ID. Requires any valid logged-in user.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle with id: {id} not found.")
    return vehicle

# --- UPDATE a vehicle by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.VehicleOut)
def update_vehicle(
    id: int,
    vehicle_data: schemas.VehicleCreate, # Using Create schema for full updates
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a vehicle's details. Requires 'admin' or 'superadmin' role.
    """
    vehicle_query = db.query(models.Vehicle).filter(models.Vehicle.id == id)
    db_vehicle = vehicle_query.first()

    if not db_vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle with id: {id} not found")

    vehicle_query.update(vehicle_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

# --- UPDATE a vehicle's status (Admin only) ---
@router.patch("/{id}/status", response_model=schemas.VehicleOut)
def update_vehicle_status(
    id: int,
    status_update: schemas.VehicleStatusUpdate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update only the status of a vehicle. Requires 'admin' or 'superadmin' role.
    """
    vehicle_query = db.query(models.Vehicle).filter(models.Vehicle.id == id)
    db_vehicle = vehicle_query.first()

    if not db_vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle with id: {id} not found")

    # You might want to add validation for the status value here
    db_vehicle.status = status_update.status
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

# --- DELETE a vehicle by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a vehicle. Requires 'admin' or 'superadmin' role.
    """
    vehicle_query = db.query(models.Vehicle).filter(models.Vehicle.id == id)
    
    if not vehicle_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle with id: {id} not found")
        
    vehicle_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)