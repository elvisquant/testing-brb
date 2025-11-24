# app/routers/dashboard_data_api.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload ,selectinload 
from sqlalchemy import func, desc, and_, or_ 
from typing import List, Optional
from datetime import datetime, timedelta, date as date_type_internal
from calendar import monthrange # For getting the last day of a month

# Adjust these imports to match your project structure
from .. import models, schemas, oauth2 
from ..database import get_db


router = APIRouter(
    prefix="/dashboard-data",  
    tags=["Dashboard Data (Aggregated)"],
    dependencies=[Depends(oauth2.get_current_user_from_header)]
)

@router.get("/kpis", response_model=schemas.KPIStats)
async def get_dashboard_kpis_data(db: Session = Depends(get_db)):
    # 1. Total Vehicles
    total_vehicles_count = db.query(func.count(models.Vehicle.id)).scalar() or 0

    # 2. Planned Trips
    # Ensure "planned" is the exact status string used in your Trip model/database
    planned_trips_count = db.query(func.count(models.Trip.id)).filter(models.Trip.status == "planned").scalar() or 0

    # 3. Repairs This Month
    today_dt = datetime.utcnow() # Using UTC for server-side consistency
    start_of_current_month = today_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Calculate end of current month robustly
    if today_dt.month == 12:
        end_of_current_month = start_of_current_month.replace(year=today_dt.year + 1, month=1) - timedelta(microseconds=1)
    else:
        end_of_current_month = start_of_current_month.replace(month=today_dt.month + 1) - timedelta(microseconds=1)
    
    repairs_this_month_count = db.query(func.count(models.Reparation.id)).filter(
        models.Reparation.repair_date >= start_of_current_month, # Assuming repair_date is DateTime
        models.Reparation.repair_date <= end_of_current_month
    ).scalar() or 0

    # 4. Fuel Cost This Week (Monday to Sunday)
    start_of_this_week = today_dt - timedelta(days=today_dt.weekday()) 
    start_of_this_week = start_of_this_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_this_week = start_of_this_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)

    total_fuel_cost_this_week = db.query(func.sum(models.Fuel.cost)).filter(
        models.Fuel.created_at >= start_of_this_week, # Assuming fuel logs have created_at
        models.Fuel.created_at <= end_of_this_week
    ).scalar() or 0.0

    return schemas.KPIStats(
        total_vehicles=total_vehicles_count,
        planned_trips=planned_trips_count,
        repairs_this_month=repairs_this_month_count,
        fuel_cost_this_week=round(total_fuel_cost_this_week, 2)
    )

@router.get("/performance-insights", response_model=schemas.PerformanceInsightsResponse)
async def get_dashboard_performance_insights(db: Session = Depends(get_db)):
    today_dt = datetime.utcnow()
    
    # Fuel Efficiency (Last month vs Current month total volume)
    # Current Month
    start_current_month = today_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if today_dt.month == 12:
        end_current_month = start_current_month.replace(year=today_dt.year + 1, month=1) - timedelta(microseconds=1)
    else:
        end_current_month = start_current_month.replace(month=today_dt.month + 1) - timedelta(microseconds=1)
    current_month_volume = db.query(func.sum(models.Fuel.quantity)).filter(
        models.Fuel.created_at >= start_current_month, models.Fuel.created_at <= end_current_month
    ).scalar() or 0.0

    # Last Month
    end_last_month = start_current_month - timedelta(microseconds=1)
    start_last_month = end_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_volume = db.query(func.sum(models.Fuel.quantity)).filter(
        models.Fuel.created_at >= start_last_month, models.Fuel.created_at <= end_last_month
    ).scalar() or 0.0

    fuel_eff_percentage_change = None
    fuel_eff_trend = "no_comparison"
    if last_month_volume > 0:
        if current_month_volume >= 0: # Allow current_month_volume to be 0
            if current_month_volume == 0: # Infinite improvement if current is 0 and last was > 0
                 percentage_change_raw = 100.0 
            else:
                # Percentage change in consumption: ((current - last) / last) * 100
                # For efficiency (lower is better): ((last - current) / last) * 100
                percentage_change_raw = ((last_month_volume - current_month_volume) / last_month_volume) * 100
            
            fuel_eff_percentage_change = round(percentage_change_raw, 1)
            if percentage_change_raw > 5: fuel_eff_trend = "up"    # Efficiency up (consumption down)
            elif percentage_change_raw < -5: fuel_eff_trend = "down" # Efficiency down (consumption up)
            else: fuel_eff_trend = "steady"
    elif current_month_volume > 0 and last_month_volume == 0: # Went from 0 consumption to some consumption
        fuel_eff_trend = "down" 
        fuel_eff_percentage_change = -100.0 # Conceptually, infinite worsening from a zero base
    # If both are 0, trend remains "no_comparison" and percentage_change is None
    
    fuel_efficiency_result = schemas.FuelEfficiencyData(
        current_month_volume=round(current_month_volume,2),
        last_month_volume=round(last_month_volume,2),
        percentage_change=fuel_eff_percentage_change,
        trend=fuel_eff_trend
    )

    # Maintenance Compliance (Total Count of all maintenance records)
    total_maintenance_records_count = db.query(func.count(models.Maintenance.id)).scalar() or 0
    maintenance_compliance_result = schemas.MaintenanceComplianceData(
        total_maintenance_records=total_maintenance_records_count
    )
    
    return schemas.PerformanceInsightsResponse(
        fuel_efficiency=fuel_efficiency_result,
        maintenance_compliance=maintenance_compliance_result
    )

@router.get("/alerts", response_model=schemas.AlertsResponse)
async def get_dashboard_alerts_data(db: Session = Depends(get_db)):
    alert_panne_item = None
    last_panne = db.query(models.Panne).options(
        joinedload(models.Panne.vehicle), 
        joinedload(models.Panne.category_panne) # Assuming relation name is 'category_panne'
    ).order_by(desc(models.Panne.panne_date)).first()
    if last_panne:
        plate = last_panne.vehicle.plate_number if last_panne.vehicle else "N/A"
        # Check if category_panne and its name attribute exist
        msg = (last_panne.category_panne.panne_name 
               if last_panne.category_panne and hasattr(last_panne.category_panne, 'panne_name') and last_panne.category_panne.panne_name 
               else (last_panne.description or "Issue details N/A"))
        alert_panne_item = schemas.AlertItem(plate_number=plate, message=msg, entity_type="panne", status=last_panne.status)

    alert_maint_item = None
    last_maint = db.query(models.Maintenance).options(
        joinedload(models.Maintenance.vehicle),
        joinedload(models.Maintenance.category_maintenance) # Assuming relation name
    ).order_by(desc(models.Maintenance.maintenance_date)).first()
    if last_maint:
        plate = last_maint.vehicle.plate_number if last_maint.vehicle else "N/A"
        maint_category_name = (last_maint.category_maintenance.cat_maintenance 
                               if last_maint.category_maintenance and hasattr(last_maint.category_maintenance, 'cat_maintenance') 
                               else "Maintenance Task")
        msg = f"{maint_category_name}"
        msg += f" (Due: {last_maint.maintenance_date.strftime('%Y-%m-%d')})" if last_maint.maintenance_date else ""
        # Assuming Maintenance model has a 'status' attribute. If not, adjust or remove.
        alert_maint_item = schemas.AlertItem(plate_number=plate, message=msg, entity_type="maintenance", status=getattr(last_maint, 'status', 'Scheduled'))

    alert_trip_item = None
    last_trip = db.query(models.Trip).options(
        joinedload(models.Trip.vehicle) # Assuming relation name is 'vehicle'
    ).order_by(desc(models.Trip.start_time)).first()
    if last_trip:
        plate = last_trip.vehicle.plate_number if last_trip.vehicle else "N/A"
        msg = f"Purpose: {last_trip.purpose or 'General Trip'}"
        alert_trip_item = schemas.AlertItem(plate_number=plate, message=msg, entity_type="trip", status=last_trip.status)
    
    total_alerts_count = sum(1 for alert in [alert_panne_item, alert_maint_item, alert_trip_item] if alert is not None)

    return schemas.AlertsResponse(
        critical_panne=alert_panne_item,
        maintenance_alert=alert_maint_item,
        trip_alert=alert_trip_item,
        total_alerts=total_alerts_count
    )

@router.get("/recent-pannes", response_model=List[schemas.PanneOut])
async def get_recent_pannes_for_dashboard(db: Session = Depends(get_db)):
    pannes = db.query(models.Panne).options(
        joinedload(models.Panne.vehicle),
        joinedload(models.Panne.category_panne)
    ).order_by(desc(models.Panne.panne_date)).limit(3).all() # Fetch 3 most recent
    return pannes


@router.get("/upcoming-trips", response_model=List[schemas.TripResponse])
async def get_upcoming_trips_for_dashboard(db: Session = Depends(get_db)):
    today_dt = datetime.utcnow() 
    trips_from_db = db.query(models.Trip).options(
        # Eager load vehicle, and from vehicle, eager load its make_ref and model_ref
        joinedload(models.Trip.vehicle).options(
            selectinload(models.Vehicle.make_ref), # Use selectinload for to-one from a collection
            selectinload(models.Vehicle.model_ref)
        ),
        joinedload(models.Trip.driver)   
    ).filter(
        models.Trip.start_time >= today_dt,
        models.Trip.status == "planned"     
    ).order_by(models.Trip.start_time.asc()).limit(3).all()
    
    # Manually construct the response list to ensure correct mapping
    response_trips: List[schemas.TripResponse] = []
    for trip_db in trips_from_db:
        vehicle_data_for_schema = None
        if trip_db.vehicle:
            # Pydantic v2 needs a dictionary to validate computed fields correctly unless the ORM instance is passed directly
            # and the schema is configured just right. This manual build is safest.
            vehicle_dict = {
                "id": trip_db.vehicle.id,
                "plate_number": trip_db.vehicle.plate_number
            }
            # Manually add the data that the computed fields rely on.
            if trip_db.vehicle.make_ref:
                vehicle_dict['make_ref'] = trip_db.vehicle.make_ref
            if trip_db.vehicle.model_ref:
                vehicle_dict['model_ref'] = trip_db.vehicle.model_ref
            
            vehicle_data_for_schema = schemas.VehicleNestedInTrip.model_validate(vehicle_dict)
        
        driver_data_for_schema = None
        if trip_db.driver:
            driver_data_for_schema = schemas.DriverNestedInTrip(
                id=trip_db.driver.id,
                first_name=trip_db.driver.first_name,
                last_name=trip_db.driver.last_name
            )

        trip_response_data = {
            "id": trip_db.id,
            "vehicle_id": trip_db.vehicle_id,
            "driver_id": trip_db.driver_id,
            "start_location": trip_db.start_location,
            "end_location": trip_db.end_location,
            "start_time": trip_db.start_time,
            "end_time": trip_db.end_time,
            "status": trip_db.status,
            "purpose": trip_db.purpose,
            "notes": trip_db.notes,
            "created_at": trip_db.created_at,
            "updated_at": trip_db.updated_at,
            "vehicle": vehicle_data_for_schema,
            "driver": driver_data_for_schema
        }
        response_trips.append(schemas.TripResponse.model_validate(trip_response_data))

    return response_trips


# --- Endpoint for Monthly Activity Chart Data ---
@router.get("/charts/monthly-activity", response_model=schemas.MonthlyActivityChartData)
async def get_monthly_activity_chart_data(db: Session = Depends(get_db), months_to_display: int = 12):
    labels = []
    trips_counts = []
    maintenances_counts = []
    pannes_counts = []
    
    today_date = datetime.utcnow().date() 

    for i in range(months_to_display -1, -1, -1):
        year_offset, month_offset = divmod(today_date.month - 1 - i, 12)
        target_year = today_date.year + year_offset
        target_month = month_offset + 1

        first_day_of_month = datetime(target_year, target_month, 1, 0, 0, 0)
        last_day_of_month_num = monthrange(target_year, target_month)[1]
        last_day_of_month = datetime(target_year, target_month, last_day_of_month_num, 23, 59, 59, 999999)
        
        labels.append(first_day_of_month.strftime("%b '%y"))

        trips_count = db.query(func.count(models.Trip.id)).filter(
            models.Trip.start_time >= first_day_of_month,
            models.Trip.start_time <= last_day_of_month
        ).scalar() or 0
        trips_counts.append(trips_count)

        maintenances_count = db.query(func.count(models.Maintenance.id)).filter(
            models.Maintenance.maintenance_date >= first_day_of_month,
            models.Maintenance.maintenance_date <= last_day_of_month
        ).scalar() or 0
        maintenances_counts.append(maintenances_count)

        pannes_count = db.query(func.count(models.Panne.id)).filter(
            models.Panne.panne_date >= first_day_of_month,
            models.Panne.panne_date <= last_day_of_month
        ).scalar() or 0
        pannes_counts.append(pannes_count)
        
    return schemas.MonthlyActivityChartData(
        labels=labels,
        trips=trips_counts,
        maintenances=maintenances_counts,
        pannes=pannes_counts
    )

# --- Endpoint for Vehicle Status Chart Data ---
@router.get("/charts/vehicle-status", response_model=schemas.VehicleStatusChartData)
async def get_vehicle_status_chart_data(db: Session = Depends(get_db)):
    status_counts_query = db.query(
        models.Vehicle.status, 
        func.count(models.Vehicle.id).label("count")
    ).group_by(models.Vehicle.status).order_by(models.Vehicle.status).all()

    labels = []
    counts = []

    display_name_map = {
        "available": "Available",
        "in_use": "In Use",
        "in_repair": "In Repair",
        "decommissioned": "Decommissioned",
        "sold": "Sold" 
    }

    for status_from_db, count in status_counts_query:
        if status_from_db is None:
            display_label = "Unknown"
        else:
            display_label = display_name_map.get(status_from_db, status_from_db.replace('_', ' ').title())
        
        labels.append(display_label)
        counts.append(count)
            
    return schemas.VehicleStatusChartData(labels=labels, counts=counts)

@router.get("/top-performing-drivers", response_model=List[schemas.TopDriver])
async def get_top_performing_drivers(
    db: Session = Depends(get_db),
    limit: int = Query(3, ge=1, le=10, description="Number of top drivers to return")
):
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    top_drivers_query = db.query(
        models.Driver.id,
        models.Driver.first_name,
        models.Driver.last_name,
        func.count(models.Trip.id).label("completed_trips_count")
    ).join(
        models.Trip, models.Driver.id == models.Trip.driver_id
    ).filter(
        models.Trip.status == "Completed",
        models.Trip.end_time >= thirty_days_ago
    ).group_by(
        models.Driver.id,
        models.Driver.first_name,
        models.Driver.last_name
    ).order_by(
        desc("completed_trips_count")
    ).limit(limit).all()

    top_drivers_list = []
    for driver_id, first_name, last_name, trips_count in top_drivers_query:
        top_drivers_list.append(schemas.TopDriver(
            driver_id=driver_id,
            first_name=first_name,
            last_name=last_name,
            performance_metric=f"{trips_count} Trips Completed"
        ))
        
    return top_drivers_list