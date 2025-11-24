# In app/routers/panne.py

from fastapi import APIRouter, Depends, status, HTTPException, Response, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/pannes",
    tags=['Pannes API']
)

# --- CREATE a new panne report (Any authenticated user) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.PanneOut)
def create_panne(
    panne_data: schemas.PanneCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can report a panne.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Creates a new panne (breakdown) report. Requires any valid logged-in user.
    """
    # Verify that the vehicle and category exist
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == panne_data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle with id {panne_data.vehicle_id} not found.")
    
    category = db.query(models.CategoryPanne).filter(models.CategoryPanne.id == panne_data.category_panne_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne category with id {panne_data.category_panne_id} not found.")

    new_panne = models.Panne(**panne_data.model_dump())
    db.add(new_panne)
    db.commit()
    db.refresh(new_panne)
    return new_panne

# --- GET all pannes (Admin only, for overview) ---
@router.get("/", response_model=schemas.PaginatedPanneOut)
def get_all_pannes(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """
    Get a paginated list of all pannes. Requires 'admin' or 'superadmin' role.
    """
    offset = (page - 1) * page_size
    
    total_count = db.query(models.Panne).count()
    
    pannes = db.query(models.Panne).options(
        joinedload(models.Panne.vehicle),
        joinedload(models.Panne.category_panne)
    ).order_by(models.Panne.panne_date.desc()).limit(page_size).offset(offset).all()
    
    return schemas.PaginatedPanneOut(total_count=total_count, items=pannes)

# --- GET a specific panne by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.PanneOut)
def get_panne_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a panne report.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single panne report by its ID. Requires any valid logged-in user.
    """
    panne = db.query(models.Panne).options(
        joinedload(models.Panne.vehicle),
        joinedload(models.Panne.category_panne)
    ).filter(models.Panne.id == id).first()
    
    if not panne:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne with id: {id} not found.")
    
    return panne

# --- UPDATE a panne by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.PanneOut)
def update_panne(
    id: int,
    panne_data: schemas.PanneUpdate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a panne report's details. Requires 'admin' or 'superadmin' role.
    """
    panne_query = db.query(models.Panne).filter(models.Panne.id == id)
    db_panne = panne_query.first()

    if not db_panne:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne with id: {id} not found")

    update_data = panne_data.model_dump(exclude_unset=True)
    panne_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(db_panne)
    
    return db_panne

# --- DELETE a panne by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_panne(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a panne report. Requires 'admin' or 'superadmin' role.
    """
    panne_query = db.query(models.Panne).filter(models.Panne.id == id)
    
    if not panne_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne with id: {id} not found")
        
    panne_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)