from sqlalchemy import Enum, Column, DateTime, Integer,Text, String,Float, ForeignKey, TIMESTAMP, text, Enum as DBEnum # Added DBEnum
from datetime import datetime
import enum
from typing import List, Optional
from datetime import datetime, date , timedelta
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.sql import func,text # For default timestamps
from .database import Base

# =================================================================================
# All models from your original file are preserved below, exactly as they were,
# except for the one critical change in VehicleRequest.
# =================================================================================

class Service(Base):
    __tablename__ = "service"
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False, index=True)
    

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    matricule = Column(String(9), unique=True, index=True, nullable=False)
    first_name = Column(String(50), index=True, nullable=False)
    last_name = Column(String(50), index=True, nullable=False)
    telephone = Column(String(25), unique=True, nullable=False)
    service_id = Column(Integer, ForeignKey("service.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False, index=True)
    status = Column(String(50), nullable=False, server_default=text("'pending'"), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text('now()'), index=True)
    service = relationship("Service")
    role = relationship("Role", back_populates="users")


class Driver(Base):
    __tablename__ = "driver"
    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=False, index=True)
    cni_number = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True, index=True)
    matricule = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), index=True)


class VehicleType(Base):
    __tablename__ = "vehicle_type"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_type = Column(String, nullable=False)


class VehicleMake(Base):
    __tablename__ = "vehicle_make"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_make = Column(String, nullable=False)


class VehicleModel(Base):
    __tablename__ = "vehicle_model"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_model = Column(String, nullable=False)


class VehicleTransmission(Base):
    __tablename__ = "vehicle_transmission"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_transmission = Column(String, nullable=False)


class FuelType(Base):
    __tablename__ = "fuel_type"
    id = Column(Integer, primary_key=True, index=True)
    fuel_type = Column(String, unique=True, index=True, nullable=False)


class Fuel(Base):
    __tablename__ = "fuel"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True)
    fuel_type_id = Column(Integer, ForeignKey("fuel_type.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    price_little = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), index=True)
    vehicle = relationship("Vehicle")


class Vehicle(Base):
    __tablename__ = "vehicle"
    id = Column(Integer, primary_key=True, index=True)
    make = Column(Integer, ForeignKey("vehicle_make.id"), index=True)
    model = Column(Integer, ForeignKey("vehicle_model.id"), index=True)
    year = Column(Integer)
    plate_number = Column(String, unique=True, nullable=False, index=True)
    mileage = Column(Float, default=0.0)
    engine_size = Column(Float, default=0.0)
    vehicle_type = Column(Integer, ForeignKey("vehicle_type.id"), index=True)
    vehicle_transmission = Column(Integer, ForeignKey("vehicle_transmission.id"), index=True)
    vehicle_fuel_type = Column(Integer, ForeignKey("fuel_type.id"), index=True)
    vin = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=False)
    purchase_price = Column(Float, default=0.0)
    purchase_date = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String, default="available", index=True)
    registration_date = Column(DateTime(timezone=True), nullable=False, server_default=text('now()'), index=True)
    make_ref = relationship("VehicleMake")
    model_ref = relationship("VehicleModel")


class VehicleRequest(Base):
    __tablename__ = 'vehicle_requests'
    id = Column(Integer, primary_key=True, index=True)
    purpose = Column(String, nullable=False)
    from_location = Column(String, nullable=False)
    to_location = Column(String, nullable=False)
    roadmap = Column(Text, nullable=True) 
    departure_time = Column(DateTime(timezone=True), nullable=False, index=True)
    return_time = Column(DateTime(timezone=True), nullable=False)
    
    # --- THIS IS THE ONE AND ONLY CHANGE ---
    status = Column(Enum(
        'pending', 
        'approved_by_chef',        
        'approved_by_logistic',     
        'fully_approved', 
        'denied', 
        'in_progress', 
        'completed', 
        name='request_status_enum'
    ), nullable=False, default='pending', index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    requester_id = Column(Integer, ForeignKey('user.id', ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(Integer, ForeignKey('vehicle.id', ondelete="SET NULL"), nullable=True, index=True)
    driver_id = Column(Integer, ForeignKey('user.id', ondelete="SET NULL"), nullable=True, index=True)
    requester = relationship("User", foreign_keys=[requester_id])
    vehicle = relationship("Vehicle")
    driver = relationship("User", foreign_keys=[driver_id])
    approvals = relationship("RequestApproval", back_populates="request", cascade="all, delete-orphan")


class RequestApproval(Base):
    __tablename__ = 'request_approvals'
    id = Column(Integer, primary_key=True, index=True)
    approval_step = Column(Integer, nullable=False)
    status = Column(Enum('pending', 'approved', 'denied', name='approval_status_enum'), nullable=False, default='pending', index=True)
    comments = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    request_id = Column(Integer, ForeignKey('vehicle_requests.id', ondelete="CASCADE"), nullable=False, index=True)
    approver_id = Column(Integer, ForeignKey('user.id', ondelete="SET NULL"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey('service.id'), nullable=True, index=True)
    service = relationship("Service")
    request = relationship("VehicleRequest", back_populates="approvals")
    approver = relationship("User")


class Garage(Base):
    __tablename__ = "garage"
    id = Column(Integer, primary_key=True, index=True)
    nom_garage = Column(String, nullable=False)


class CategoryMaintenance(Base):
    __tablename__ = "category_maintenance"
    id = Column(Integer, primary_key=True, index=True)
    cat_maintenance = Column(String, nullable=False)

  
class Maintenance(Base):
    __tablename__ = "maintenance"
    id = Column(Integer, primary_key=True, index=True)
    cat_maintenance_id = Column(Integer, ForeignKey("category_maintenance.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True)
    garage_id = Column(Integer, ForeignKey("garage.id", ondelete="SET NULL"), nullable=True, index=True)
    maintenance_cost = Column(Float, default=0.0, nullable=False)
    receipt = Column(String, nullable=False)
    maintenance_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), index=True)
    status = Column(String(50), default="active", nullable=False, index=True)
    vehicle = relationship("Vehicle") 
    category_maintenance = relationship("CategoryMaintenance")
    garage = relationship("Garage")
   

class CategoryPanne(Base):
    __tablename__ = "category_panne"
    id = Column(Integer, primary_key=True, index=True)
    panne_name = Column(String, nullable=False)


class Panne(Base):
    __tablename__ = "panne"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id"), nullable=False, index=True)
    category_panne_id = Column(Integer, ForeignKey("category_panne.id"), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    status = Column(String(50), default="active", nullable=False, index=True)
    panne_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), index=True)
    vehicle = relationship("Vehicle")
    category_panne = relationship("CategoryPanne")


class Reparation(Base):
    __tablename__ = "reparation"
    id = Column(Integer, primary_key=True, index=True)
    panne_id = Column(Integer, ForeignKey("panne.id"), index=True)
    cost = Column(Float, default=0.0)
    receipt = Column(String, nullable=False)
    garage_id = Column(Integer, ForeignKey("garage.id"), index=True)
    repair_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    status = Column(String, default="Inprogress", index=True)
    panne = relationship("Panne")
    garage = relationship("Garage")


class Trip(Base):
    __tablename__ = "trip"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("driver.id"), nullable=False, index=True)
    start_location = Column(String, nullable=False)
    end_location = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True, index=True)
    purpose = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    status = Column(String, nullable=False, default="planned", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    vehicle = relationship("Vehicle")
    driver = relationship("Driver")