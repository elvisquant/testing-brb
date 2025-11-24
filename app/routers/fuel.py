# In app/routers/fuel.py

from fastapi import APIRouter, Depends, HTTPException, status, Query,Response
from sqlalchemy.orm import Session
from sqlalchemy import desc # For ordering
from typing import List, Optional
from datetime import date as date_type, datetime # For potential date filtering

# Assuming your project structure is app/routers, app/models, app/schemas, app/database
from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/fuel", # Using a standard API prefix
    tags=['Fuel Records API']
)

@router.post("/", response_model=schemas.FuelOut, status_code=status.HTTP_201_CREATED)
def create_new_fuel_record(
    fuel_payload: schemas.FuelCreatePayload,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any authenticated user can create a fuel record.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Create a new fuel record. Requires any valid logged-in user.
    'cost' is automatically calculated by the server as quantity * price_little.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == fuel_payload.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Vehicle with ID {fuel_payload.vehicle_id} not found.")

    fuel_type = db.query(models.FuelType).filter(models.FuelType.id == fuel_payload.fuel_type_id).first()
    if not fuel_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Fuel Type with ID {fuel_payload.fuel_type_id} not found.")

    if fuel_payload.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Fuel quantity must be greater than zero.")
    if fuel_payload.price_little <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Price per unit (price_little) must be greater than zero.")

    calculated_cost = round(fuel_payload.quantity * fuel_payload.price_little, 2)

    db_fuel_record = models.Fuel(
        vehicle_id=fuel_payload.vehicle_id,
        fuel_type_id=fuel_payload.fuel_type_id,
        quantity=fuel_payload.quantity,
        price_little=fuel_payload.price_little,
        cost=calculated_cost
    )
    
    db.add(db_fuel_record)
    db.commit()
    db.refresh(db_fuel_record)
    return db_fuel_record

@router.get("/{fuel_id}", response_model=schemas.FuelOut)
def read_fuel_record_by_id(
    fuel_id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any authenticated user can view a fuel record.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Get a specific fuel record by its ID. Requires any valid logged-in user.
    """
    db_fuel_record = db.query(models.Fuel).filter(models.Fuel.id == fuel_id).first()
    if db_fuel_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel record not found")
    return db_fuel_record

@router.get("/", response_model=List[schemas.FuelOut])
def read_all_fuel_records(
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any authenticated user can view the list of fuel records.
    current_user: models.User = Depends(oauth2.get_current_user_from_header),
    skip: int = Query(0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    vehicle_id_filter: Optional[int] = Query(default=None, alias="vehicle_id"),
    fuel_type_id_filter: Optional[int] = Query(default=None, alias="fuel_type_id"),
    date_after: Optional[date_type] = Query(default=None),
    date_before: Optional[date_type] = Query(default=None)
):
    """
    Retrieve a list of fuel records with optional filtering and pagination.
    """
    query = db.query(models.Fuel)

    if vehicle_id_filter is not None:
        query = query.filter(models.Fuel.vehicle_id == vehicle_id_filter)
    if fuel_type_id_filter is not None:
        query = query.filter(models.Fuel.fuel_type_id == fuel_type_id_filter)
    if date_after:
        query = query.filter(models.Fuel.created_at >= datetime.combine(date_after, datetime.min.time()))
    if date_before:
        query = query.filter(models.Fuel.created_at <= datetime.combine(date_before, datetime.max.time()))
    
    fuel_records = query.order_by(desc(models.Fuel.created_at)).offset(skip).limit(limit).all()
    return fuel_records

@router.put("/{fuel_id}", response_model=schemas.FuelOut)
def update_existing_fuel_record(
    fuel_id: int,
    fuel_payload: schemas.FuelUpdatePayload,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Updating records should be an admin-level action.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Update an existing fuel record. Requires admin role.
    If quantity or price_little are updated, 'cost' will be automatically recalculated.
    """
    db_fuel_record = db.query(models.Fuel).filter(models.Fuel.id == fuel_id).first()
    if not db_fuel_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel record not found for update")

    update_data = fuel_payload.model_dump(exclude_unset=True)

    if "vehicle_id" in update_data and update_data["vehicle_id"] != db_fuel_record.vehicle_id:
        vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == update_data["vehicle_id"]).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"New vehicle with ID {update_data['vehicle_id']} not found.")
    
    if "fuel_type_id" in update_data and update_data["fuel_type_id"] != db_fuel_record.fuel_type_id:
        fuel_type = db.query(models.FuelType).filter(models.FuelType.id == update_data["fuel_type_id"]).first()
        if not fuel_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"New Fuel Type with ID {update_data['fuel_type_id']} not found.")

    recalculate_cost_flag = False
    effective_quantity = db_fuel_record.quantity
    effective_price_little = db_fuel_record.price_little

    if "quantity" in update_data:
        if update_data["quantity"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fuel quantity must be greater than zero.")
        effective_quantity = update_data["quantity"]
        recalculate_cost_flag = True
    
    if "price_little" in update_data:
        if update_data["price_little"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price per unit must be greater than zero.")
        effective_price_little = update_data["price_little"]
        recalculate_cost_flag = True

    if recalculate_cost_flag:
        update_data['cost'] = round(effective_quantity * effective_price_little, 2)
    
    for key, value in update_data.items():
        setattr(db_fuel_record, key, value)

    db.commit()
    db.refresh(db_fuel_record)
    return db_fuel_record

@router.delete("/{fuel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_fuel_record(
    fuel_id: int,
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Deleting records must be an admin-level action.
    current_user: models.User = Depends(oauth2.require_admin_role_for_api)
):
    """
    Delete a fuel record by its ID. Requires admin role.
    """
    db_fuel_record = db.query(models.Fuel).filter(models.Fuel.id == fuel_id).first()
    if db_fuel_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel record not found for deletion")

    db.delete(db_fuel_record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/check-eligibility/{vehicle_id}", response_model=schemas.EligibilityResponse)
def check_fuel_eligibility(
    vehicle_id: int, 
    db: Session = Depends(get_db),
    # CORRECTED DEPENDENCY: Any authenticated user can check eligibility.
    current_user: models.User = Depends(oauth2.get_current_user_from_header)
):
    """
    Checks if a vehicle is eligible for fueling based on business rules.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Vehicle with ID {vehicle_id} not found."}
        )

    if vehicle.status != 'available':
        # This is a business rule failure, not an authentication error, so we don't raise a 401/403.
        # Returning a specific structure is better for the frontend.
        return schemas.EligibilityResponse(
            eligible=False,
            message=f"Vehicle is not eligible for fueling. Its current status is '{vehicle.status}'."
        )

    last_fuel_record = db.query(models.Fuel).filter(
        models.Fuel.vehicle_id == vehicle_id
    ).order_by(desc(models.Fuel.created_at)).first()

    if last_fuel_record:
        last_fueling_time = last_fuel_record.created_at

        completed_trip_exists = db.query(models.Trip).filter(
            models.Trip.vehicle_id == vehicle_id,
            models.Trip.status == 'Completed',
            models.Trip.end_time > last_fueling_time
        ).first()

        if not completed_trip_exists:
            return schemas.EligibilityResponse(
                eligible=False,
                message="A completed trip is required since the last refueling on " + last_fueling_time.strftime('%Y-%m-%d %H:%M')
            )

    return schemas.EligibilityResponse(
        eligible=True,
        message="Vehicle is eligible for fueling."
    )