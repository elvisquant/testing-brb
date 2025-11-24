# In app/routers/reparation.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session, joinedload
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/reparations",
    tags=['Reparations API']
)

# --- CREATE a new reparation record (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ReparationResponse)
def create_reparation(
    reparation_data: schemas.ReparationCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new reparation record for a specific panne. Requires 'admin' or 'superadmin' role.
    """
    # Verify that the panne and garage exist
    panne = db.query(models.Panne).filter(models.Panne.id == reparation_data.panne_id).first()
    if not panne:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne with id {reparation_data.panne_id} not found.")
    
    garage = db.query(models.Garage).filter(models.Garage.id == reparation_data.garage_id).first()
    if not garage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Garage with id {reparation_data.garage_id} not found.")

    new_reparation = models.Reparation(**reparation_data.model_dump())
    
    # Optionally, update the status of the related panne
    panne.status = "in_progress" # Or whatever status you use
    
    db.add(new_reparation)
    db.commit()
    db.refresh(new_reparation)
    return new_reparation

# --- GET all reparations (Admin only) ---
@router.get("/", response_model=List[schemas.ReparationResponse])
def get_all_reparations(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Get a list of all reparation records. Requires 'admin' or 'superadmin' role.
    """
    reparations = db.query(models.Reparation).options(
        joinedload(models.Reparation.panne),
        joinedload(models.Reparation.garage)
    ).order_by(models.Reparation.repair_date.desc()).all()
    return reparations

# --- GET a specific reparation by ID (Admin only) ---
@router.get("/{id}", response_model=schemas.ReparationResponse)
def get_reparation_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Get a single reparation record by its ID. Requires 'admin' or 'superadmin' role.
    """
    reparation = db.query(models.Reparation).options(
        joinedload(models.Reparation.panne),
        joinedload(models.Reparation.garage)
    ).filter(models.Reparation.id == id).first()
    
    if not reparation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reparation with id: {id} not found.")
    
    return reparation

# --- UPDATE a reparation by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.ReparationResponse)
def update_reparation(
    id: int,
    reparation_data: schemas.ReparationUpdate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a reparation record. Requires 'admin' or 'superadmin' role.
    """
    reparation_query = db.query(models.Reparation).filter(models.Reparation.id == id)
    db_reparation = reparation_query.first()

    if not db_reparation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reparation with id: {id} not found")

    update_data = reparation_data.model_dump(exclude_unset=True)
    reparation_query.update(update_data, synchronize_session=False)

    # If the reparation is marked as 'Completed', update the related panne's status
    if update_data.get("status") == schemas.ReparationStatusEnum.COMPLETED:
        panne = db.query(models.Panne).filter(models.Panne.id == db_reparation.panne_id).first()
        if panne:
            panne.status = "resolved"

    db.commit()
    db.refresh(db_reparation)
    
    return db_reparation

# --- DELETE a reparation by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reparation(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a reparation record. Requires 'admin' or 'superadmin' role.
    """
    reparation_query = db.query(models.Reparation).filter(models.Reparation.id == id)
    
    if not reparation_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reparation with id: {id} not found")
        
    reparation_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)