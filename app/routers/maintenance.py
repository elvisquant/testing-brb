# In app/routers/maintenance.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session, joinedload
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/maintenances",
    tags=['Maintenances API']
)

# --- CREATE a new maintenance record (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.MaintenanceOut)
def create_maintenance(
    maintenance_data: schemas.MaintenanceCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new maintenance record for a vehicle. Requires 'admin' or 'superadmin' role.
    """
    # Verify that the vehicle, category, and garage exist
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == maintenance_data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle with id {maintenance_data.vehicle_id} not found.")
    
    if maintenance_data.cat_maintenance_id:
        category = db.query(models.CategoryMaintenance).filter(models.CategoryMaintenance.id == maintenance_data.cat_maintenance_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance category with id {maintenance_data.cat_maintenance_id} not found.")

    if maintenance_data.garage_id:
        garage = db.query(models.Garage).filter(models.Garage.id == maintenance_data.garage_id).first()
        if not garage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Garage with id {maintenance_data.garage_id} not found.")

    new_maintenance = models.Maintenance(**maintenance_data.model_dump())
    db.add(new_maintenance)
    db.commit()
    db.refresh(new_maintenance)
    return new_maintenance

# --- GET all maintenance records (Admin only) ---
@router.get("/", response_model=List[schemas.MaintenanceOut])
def get_all_maintenances(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Get a list of all maintenance records. Requires 'admin' or 'superadmin' role.
    """
    maintenances = db.query(models.Maintenance).order_by(models.Maintenance.maintenance_date.desc()).all()
    return maintenances

# --- GET a specific maintenance record by ID (Admin only) ---
@router.get("/{id}", response_model=schemas.MaintenanceOut)
def get_maintenance_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Get a single maintenance record by its ID. Requires 'admin' or 'superadmin' role.
    """
    maintenance = db.query(models.Maintenance).filter(models.Maintenance.id == id).first()
    if not maintenance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance record with id: {id} not found.")
    return maintenance

# --- UPDATE a maintenance record by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.MaintenanceOut)
def update_maintenance(
    id: int,
    maintenance_data: schemas.MaintenanceUpdate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a maintenance record. Requires 'admin' or 'superadmin' role.
    """
    maintenance_query = db.query(models.Maintenance).filter(models.Maintenance.id == id)
    db_maintenance = maintenance_query.first()

    if not db_maintenance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance record with id: {id} not found")

    update_data = maintenance_data.model_dump(exclude_unset=True)
    maintenance_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(db_maintenance)
    return db_maintenance

# --- DELETE a maintenance record by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintenance(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a maintenance record. Requires 'admin' or 'superadmin' role.
    """
    maintenance_query = db.query(models.Maintenance).filter(models.Maintenance.id == id)
    
    if not maintenance_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance record with id: {id} not found")
        
    maintenance_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)