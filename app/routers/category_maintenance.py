# In app/routers/category_maintenance.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/maintenance-categories",
    tags=['Maintenance Categories API']
)

# --- CREATE a new maintenance category (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CategoryMaintenanceOut)
def create_maintenance_category(
    category_data: schemas.CategoryMaintenanceCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new maintenance category (e.g., 'Oil Change', 'Tire Rotation'). Requires 'admin' or 'superadmin' role.
    """
    # Check if a category with the same name already exists (case-insensitive)
    existing_category = db.query(models.CategoryMaintenance).filter(
        models.CategoryMaintenance.cat_maintenance.ilike(category_data.cat_maintenance)
    ).first()
    if existing_category:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Maintenance category '{category_data.cat_maintenance}' already exists.")

    new_category = models.CategoryMaintenance(**category_data.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

# --- GET all maintenance categories (Any authenticated user) ---
@router.get("/", response_model=List[schemas.CategoryMaintenanceOut])
def get_all_maintenance_categories(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of categories.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available maintenance categories. Requires any valid logged-in user.
    """
    categories_list = db.query(models.CategoryMaintenance).order_by(models.CategoryMaintenance.cat_maintenance).all()
    return categories_list

# --- GET a specific maintenance category by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.CategoryMaintenanceOut)
def get_maintenance_category_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single category.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single maintenance category by its ID. Requires any valid logged-in user.
    """
    category = db.query(models.CategoryMaintenance).filter(models.CategoryMaintenance.id == id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance category with id: {id} not found.")
    return category

# --- UPDATE a maintenance category by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.CategoryMaintenanceOut)
def update_maintenance_category(
    id: int,
    category_data: schemas.CategoryMaintenanceCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a maintenance category's details. Requires 'admin' or 'superadmin' role.
    """
    category_query = db.query(models.CategoryMaintenance).filter(models.CategoryMaintenance.id == id)
    db_category = category_query.first()

    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance category with id: {id} not found")

    # Check for name conflict before updating
    if category_data.cat_maintenance.lower() != db_category.cat_maintenance.lower():
        existing_category = db.query(models.CategoryMaintenance).filter(
            models.CategoryMaintenance.cat_maintenance.ilike(category_data.cat_maintenance)
        ).first()
        if existing_category:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Maintenance category '{category_data.cat_maintenance}' already exists.")

    category_query.update(category_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_category)
    return db_category

# --- DELETE a maintenance category by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintenance_category(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a maintenance category. Requires 'admin' or 'superadmin' role.
    """
    category_query = db.query(models.CategoryMaintenance).filter(models.CategoryMaintenance.id == id)
    
    if not category_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance category with id: {id} not found")
        
    category_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)