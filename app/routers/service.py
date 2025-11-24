# In app/routers/service.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/services",
    tags=['Services API']
)

# --- CREATE a new service (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ServiceOut)
def create_service(
    service_data: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new service. Requires 'admin' or 'superadmin' role.
    """
    # Check if a service with the same name already exists
    existing_service = db.query(models.Service).filter(models.Service.service_name == service_data.service_name).first()
    if existing_service:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Service with name '{service_data.service_name}' already exists.")

    new_service = models.Service(**service_data.model_dump())
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service

# --- GET all services (Any authenticated user) ---
@router.get("/", response_model=List[schemas.ServiceOut])
def get_all_services(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available services. Requires any valid logged-in user.
    """
    # === THIS IS THE FIX ===
    # Changed models.Service.name to the correct column name: models.Service.service_name
    services = db.query(models.Service).order_by(models.Service.service_name).all()
    return services

# --- GET a specific service by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.ServiceOut)
def get_service_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single service by its ID. Requires any valid logged-in user.
    """
    service = db.query(models.Service).filter(models.Service.id == id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service with id: {id} not found.")
    return service

# --- UPDATE a service by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.ServiceOut)
def update_service(
    id: int,
    service_data: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a service's details. Requires 'admin' or 'superadmin' role.
    """
    service_query = db.query(models.Service).filter(models.Service.id == id)
    db_service = service_query.first()

    if not db_service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service with id: {id} not found")

    # Check for name conflict before updating
    if service_data.service_name != db_service.service_name:
        existing_service = db.query(models.Service).filter(models.Service.service_name == service_data.service_name).first()
        if existing_service:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Service with name '{service_data.service_name}' already exists.")

    service_query.update(service_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_service)
    return db_service

# --- DELETE a service by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a service. Requires 'admin' or 'superadmin' role.
    """
    service_query = db.query(models.Service).filter(models.Service.id == id)
    
    if not service_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service with id: {id} not found")
        
    service_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)