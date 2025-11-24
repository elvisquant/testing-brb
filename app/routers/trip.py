# app/routers/trip.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload 
from sqlalchemy import or_ # For search queries
from typing import List, Optional
from datetime import date as date_type, datetime

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/trip",
    tags=['Trips'],
    #dependencies=[Depends(oauth2.get_current_user)]
)

@router.post("/", response_model=schemas.TripResponse, status_code=status.HTTP_201_CREATED)
def create_new_trip(
    trip_payload: schemas.TripCreate,
    db: Session = Depends(get_db)
):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == trip_payload.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Vehicle with ID {trip_payload.vehicle_id} not found.")
    # Example: if hasattr(vehicle, 'status') and vehicle.status != "available":
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Vehicle {vehicle.id} is not available.")

    driver = db.query(models.Driver).filter(models.Driver.id == trip_payload.driver_id).first()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Driver with ID {trip_payload.driver_id} not found.")
    # Example: if hasattr(driver, 'status') and driver.status != "active":
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Driver {driver.id} is not active.")

    # Basic overlap check (simplified, can be more robust)
    # This example only checks if a vehicle or driver is involved in *any* trip that might overlap.
    # A more precise check would compare start_time and end_time ranges.
    if trip_payload.end_time: # Only check overlap if trip has a defined end time
        overlapping_query = db.query(models.Trip).filter(
            or_(models.Trip.vehicle_id == trip_payload.vehicle_id, models.Trip.driver_id == trip_payload.driver_id),
            models.Trip.end_time > trip_payload.start_time, # Existing trip ends after new one starts
            models.Trip.start_time < trip_payload.end_time    # Existing trip starts before new one ends
        )
        if overlapping_query.first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Vehicle or driver has an overlapping trip scheduled for the given time.")


    db_trip = models.Trip(**trip_payload.model_dump())
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip

@router.get("/{trip_id}", response_model=schemas.TripResponse)
def read_trip_by_id(
    trip_id: int,
    db: Session = Depends(get_db)
):
    db_trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if db_trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return db_trip

""" @router.get("/", response_model=List[schemas.TripResponse])
def read_all_trips(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=1000),
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    vehicle_id_filter: Optional[int] = Query(default=None, alias="vehicle_id"),
    driver_id_filter: Optional[int] = Query(default=None, alias="driver_id"),
    start_date_after: Optional[date_type] = Query(default=None),
    start_date_before: Optional[date_type] = Query(default=None)
):
    query = db.query(models.Trip)

    if search:
        search_term = f"%{search}%"
        # Join with vehicle and driver tables to search their names/plates
        query = query.join(models.Vehicle, models.Trip.vehicle_id == models.Vehicle.id, isouter=True)\
                     .join(models.Driver, models.Trip.driver_id == models.Driver.id, isouter=True)

        query = query.filter(
            or_(
                models.Trip.start_location.ilike(search_term),
                models.Trip.end_location.ilike(search_term),
                models.Trip.purpose.ilike(search_term),
                models.Trip.notes.ilike(search_term),
                models.Vehicle.plate_number.ilike(search_term), # Assuming Vehicle model has plate_number
                models.Driver.first_name.ilike(search_term),   # Assuming Driver model has first_name
                models.Driver.last_name.ilike(search_term)    # Assuming Driver model has last_name
            )
        )

    if status_filter:
        query = query.filter(models.Trip.status == status_filter)
    if vehicle_id_filter:
        query = query.filter(models.Trip.vehicle_id == vehicle_id_filter)
    if driver_id_filter:
        query = query.filter(models.Trip.driver_id == driver_id_filter)
    if start_date_after:
        query = query.filter(models.Trip.start_time >= datetime.combine(start_date_after, datetime.min.time()))
    if start_date_before:
        query = query.filter(models.Trip.start_time <= datetime.combine(start_date_before, datetime.max.time()))

    trips = query.order_by(models.Trip.start_time.desc()).offset(skip).limit(limit).all()
    return trips """


@router.get("/", response_model=List[schemas.TripResponse])
def read_all_trips(
    db: Session = Depends(get_db),
    skip: int = 0,
    #limit: int = Query(default=100, ge=1, le=1000),
    limit: int = 1000,
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    vehicle_id_filter: Optional[int] = Query(default=None, alias="vehicle_id"),
    driver_id_filter: Optional[int] = Query(default=None, alias="driver_id"),
    start_date_after: Optional[date_type] = Query(default=None),
    start_date_before: Optional[date_type] = Query(default=None)
):
    # Start with the base query and apply eager loading options
    query = db.query(models.Trip).options(
        selectinload(models.Trip.vehicle).selectinload(models.Vehicle.make_ref),  # Eager load Trip -> Vehicle -> VehicleMake
        selectinload(models.Trip.vehicle).selectinload(models.Vehicle.model_ref), # Eager load Trip -> Vehicle -> VehicleModel
        selectinload(models.Trip.driver)  # Eager load Trip -> Driver
    )

    if search:
        search_term = f"%{search}%"
        # Apply joins for filtering. These joins are for the WHERE clause.
        # The selectinload options define what's loaded in the SELECT part.
        # Note: If searching by make/model names, ensure VehicleMake/VehicleModel are also joined.
        search_query_joins = query.join(models.Vehicle, models.Trip.vehicle_id == models.Vehicle.id, isouter=True)\
                                  .join(models.Driver, models.Trip.driver_id == models.Driver.id, isouter=True)
        
        # For searching by make/model string name, you'd need to join further:
        # search_query_joins = search_query_joins.join(models.Vehicle.make_ref, isouter=True) \
        #                                        .join(models.Vehicle.model_ref, isouter=True)
        
        query = search_query_joins.filter( # Use the query with joins for filtering
            or_(
                models.Trip.start_location.ilike(search_term),
                models.Trip.end_location.ilike(search_term),
                models.Trip.purpose.ilike(search_term),
                models.Trip.notes.ilike(search_term),
                models.Vehicle.plate_number.ilike(search_term),
                # To search by make/model name:
                # models.VehicleMake.vehicle_make.ilike(search_term),
                # models.VehicleModel.vehicle_model.ilike(search_term),
                models.Driver.first_name.ilike(search_term),
                models.Driver.last_name.ilike(search_term)
            )
        )

    if status_filter:
        query = query.filter(models.Trip.status == status_filter)
    if vehicle_id_filter:
        query = query.filter(models.Trip.vehicle_id == vehicle_id_filter)
    if driver_id_filter:
        query = query.filter(models.Trip.driver_id == driver_id_filter)
    if start_date_after:
        query = query.filter(models.Trip.start_time >= datetime.combine(start_date_after, datetime.min.time()))
    if start_date_before:
        query = query.filter(models.Trip.start_time <= datetime.combine(start_date_before, datetime.max.time()))

    trips = query.order_by(models.Trip.start_time.desc()).offset(skip).limit(limit).all()
    return trips


@router.put("/{trip_id}", response_model=schemas.TripResponse)
def update_existing_trip(
    trip_id: int,
    trip_payload: schemas.TripUpdate,
    db: Session = Depends(get_db)
):
    db_trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found for update")

    update_data = trip_payload.model_dump(exclude_unset=True)

    if "vehicle_id" in update_data and update_data["vehicle_id"] != db_trip.vehicle_id:
        vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == update_data["vehicle_id"]).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"New vehicle with ID {update_data['vehicle_id']} not found.")
        # Example: if hasattr(vehicle, 'status') and vehicle.status != "available":
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"New vehicle {update_data['vehicle_id']} is not available.")


    if "driver_id" in update_data and update_data["driver_id"] != db_trip.driver_id:
        driver = db.query(models.Driver).filter(models.Driver.id == update_data["driver_id"]).first()
        if not driver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"New driver with ID {update_data['driver_id']} not found.")
        # Example: if hasattr(driver, 'status') and driver.status != "active":
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"New driver {update_data['driver_id']} is not active.")

    # Basic overlap check for update (simplified)
    check_start_time = update_data.get("start_time", db_trip.start_time)
    check_end_time = update_data.get("end_time") # Could be None if unsetting
    if 'end_time' not in update_data and trip_payload.model_fields_set and 'end_time' not in trip_payload.model_fields_set:
         check_end_time = db_trip.end_time # Retain existing end_time if not in payload to unset
    elif 'end_time' in update_data and update_data['end_time'] is None:
        check_end_time = None # Explicitly set to None


    check_vehicle_id = update_data.get("vehicle_id", db_trip.vehicle_id)
    check_driver_id = update_data.get("driver_id", db_trip.driver_id)

    if check_end_time: # Only check overlap if trip has a defined end time
        overlapping_query = db.query(models.Trip).filter(
            models.Trip.id != trip_id, # Exclude self
            or_(models.Trip.vehicle_id == check_vehicle_id, models.Trip.driver_id == check_driver_id),
            models.Trip.end_time > check_start_time,
            models.Trip.start_time < check_end_time
        )
        if overlapping_query.first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="The updated trip details would cause an overlap with another trip.")


    for key, value in update_data.items():
        setattr(db_trip, key, value)

    db.commit()
    db.refresh(db_trip)
    return db_trip

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_trip(
    trip_id: int,
    db: Session = Depends(get_db)
):
    db_trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if db_trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found for deletion")

    # Example: if db_trip.status in ["ongoing", "completed"]:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot delete trip in '{db_trip.status}' status.")

    db.delete(db_trip)
    db.commit()
    return