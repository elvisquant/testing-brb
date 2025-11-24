# In app/routers/category_panne.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    # Standard API prefix
    prefix="/api/v1/panne-categories",
    tags=['Panne Categories API']
)

# --- CREATE a new panne category (Admin only) ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CategoryPanneOut)
def create_panne_category(
    category_data: schemas.CategoryPanneCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Creates a new panne (breakdown) category (e.g., 'Engine Failure', 'Flat Tire').
    Requires 'admin' or 'superadmin' role.
    """
    # Check if a category with the same name already exists (case-insensitive)
    existing_category = db.query(models.CategoryPanne).filter(
        models.CategoryPanne.panne_name.ilike(category_data.panne_name)
    ).first()
    if existing_category:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Panne category '{category_data.panne_name}' already exists.")

    new_category = models.CategoryPanne(**category_data.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

# --- GET all panne categories (Any authenticated user) ---
@router.get("/", response_model=List[schemas.CategoryPanneOut])
def get_all_panne_categories(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view the list of categories.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a list of all available panne categories. Requires any valid logged-in user.
    """
    categories_list = db.query(models.CategoryPanne).order_by(models.CategoryPanne.panne_name).all()
    return categories_list

# --- GET a specific panne category by ID (Any authenticated user) ---
@router.get("/{id}", response_model=schemas.CategoryPanneOut)
def get_panne_category_by_id(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any logged-in user can view a single category.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a single panne category by its ID. Requires any valid logged-in user.
    """
    category = db.query(models.CategoryPanne).filter(models.CategoryPanne.id == id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne category with id: {id} not found.")
    return category

# --- UPDATE a panne category by ID (Admin only) ---
@router.put("/{id}", response_model=schemas.CategoryPanneOut)
def update_panne_category(
    id: int,
    category_data: schemas.CategoryPanneCreate,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update a panne category's details. Requires 'admin' or 'superadmin' role.
    """
    category_query = db.query(models.CategoryPanne).filter(models.CategoryPanne.id == id)
    db_category = category_query.first()

    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne category with id: {id} not found")

    # Check for name conflict before updating
    if category_data.panne_name.lower() != db_category.panne_name.lower():
        existing_category = db.query(models.CategoryPanne).filter(
            models.CategoryPanne.panne_name.ilike(category_data.panne_name)
        ).first()
        if existing_category:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Panne category '{category_data.panne_name}' already exists.")

    category_query.update(category_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(db_category)
    return db_category

# --- DELETE a panne category by ID (Admin only) ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_panne_category(
    id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Use the function for API calls needing admin role.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a panne category. Requires 'admin' or 'superadmin' role.
    """
    category_query = db.query(models.CategoryPanne).filter(models.CategoryPanne.id == id)
    
    if not category_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Panne category with id: {id} not found")
        
    category_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)