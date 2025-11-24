# In app/routers/vehicle_model.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/vehicle-models",
    tags=['Vehicle Models API']
)

# --- CREATE a new vehicle model (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.VehicleModelOut)
def create_vehicle_model(
    model_data: schemas.VehicleModelCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new vehicle model (e.g., 'Corolla', 'F-150'). Requires 'admin' or 'superadmin' role.
    """
    # Check if a model with the same name already exists (case-insensitive)
    existing_model = db.query(models.VehicleModel).filter(
        models.VehicleModel.vehicle_model.ilike(model_data.vehicle_model)
    ).first()
    if existing_model:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle model '{model_data.vehicle_model}' already exists.")

    new_model = models.VehicleModel(**model_data.model_dump())
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    return new_model

# --- GET all vehicle models (Any authenticated user) ---
@router.get("/", response_model=List[schemas.VehicleModelOut])
def get_all_vehicle_models(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of models.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available vehicle models. Requires any valid logged-in user.
    """
    models_list = db.query(models.VehicleModel).order_by(models.VehicleModel.vehicle_model).all()
    return models_list

# --- GET a specific vehicle model by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.VehicleModelOut)
def get_vehicle_model_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single model.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single vehicle model by its ID. Requires any valid logged-in user.
    """
    model = db.query(models.VehicleModel).filter(models.VehicleModel.id == id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle model with id: {id} not found.")
    return model

# --- UPDATE a vehicle model by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.VehicleModelOut)
def update_vehicle_model(
    id: int,
    model_data: schemas.VehicleModelCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a vehicle model's details. Requires 'admin' or 'superadmin' role.
    """
    model_query = db.query(models.VehicleModel).filter(models.VehicleModel.id == id)
    db_model = model_query.first()

    if not db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle model with id: {id} not found")

    # Check for name conflict before updating
    if model_data.vehicle_model.lower() != db_model.vehicle_model.lower():
        existing_model = db.query(models.VehicleModel).filter(
            models.VehicleModel.vehicle_model.ilike(model_data.vehicle_model)
        ).first()
        if existing_model:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Vehicle model '{model_data.vehicle_model}' already exists.")

    model_query.update(model_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_model)
    return db_model

# --- DELETE a vehicle model by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_model(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a vehicle model. Requires 'admin' or 'superadmin' role.
    """
    model_query = db.query(models.VehicleModel).filter(models.VehicleModel.id == id)
    
    if not model_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vehicle model with id: {id} not found")
        
    model_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)