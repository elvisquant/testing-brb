# In app/routers/garage.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/garages",
    tags=['Garages API']
)

# --- CREATE a new garage (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.GarageOut)
def create_garage(
    garage_data: schemas.GarageCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new garage. Requires 'admin' or 'superadmin' role.
    """
    # Check if a garage with the same name already exists (case-insensitive)
    existing_garage = db.query(models.Garage).filter(models.Garage.nom_garage.ilike(garage_data.nom_garage)).first()
    if existing_garage:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Garage with name '{garage_data.nom_garage}' already exists.")

    new_garage = models.Garage(**garage_data.model_dump())
    db.add(new_garage)
    db.commit()
    db.refresh(new_garage)
    return new_garage

# --- GET all garages (Any authenticated user) ---
@router.get("/", response_model=List[schemas.GarageOut])
def get_all_garages(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of garages.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available garages. Requires any valid logged-in user.
    """
    garages = db.query(models.Garage).order_by(models.Garage.nom_garage).all()
    return garages

# --- GET a specific garage by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.GarageOut)
def get_garage_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single garage.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single garage by its ID. Requires any valid logged-in user.
    """
    garage = db.query(models.Garage).filter(models.Garage.id == id).first()
    if not garage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Garage with id: {id} not found.")
    return garage

# --- UPDATE a garage by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.GarageOut)
def update_garage(
    id: int,
    garage_data: schemas.GarageCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a garage's details. Requires 'admin' or 'superadmin' role.
    """
    garage_query = db.query(models.Garage).filter(models.Garage.id == id)
    db_garage = garage_query.first()

    if not db_garage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Garage with id: {id} not found")

    # Check for name conflict before updating
    if garage_data.nom_garage.lower() != db_garage.nom_garage.lower():
        existing_garage = db.query(models.Garage).filter(models.Garage.nom_garage.ilike(garage_data.nom_garage)).first()
        if existing_garage:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Garage with name '{garage_data.nom_garage}' already exists.")

    garage_query.update(garage_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_garage)
    return db_garage

# --- DELETE a garage by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_garage(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a garage. Requires 'admin' or 'superadmin' role.
    """
    garage_query = db.query(models.Garage).filter(models.Garage.id == id)
    
    if not garage_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Garage with id: {id} not found")
        
    garage_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)