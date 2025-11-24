# In app/main.py

import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# --- Core App Imports ---
from . import models, oauth2
from .database import engine
from fastapi.staticfiles import StaticFiles

# --- Router Imports (No Duplicates) ---
from .routers import (
    auth, user, service, role, request, approval, vehicle, trip,
    maintenance, panne, reparation, fuel, garage, fuel_type,
    vehicle_make, vehicle_model, vehicle_type, vehicle_transmission, 
    category_maintenance, category_panne, 
    dashboard_data_api, analytics_api
)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="FleetDash Application",
    description="API and Frontend for fleet management.",
    version="1.1.0",
)

# --- CORS Middleware ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Directory and Template Setup ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- Include All API Routers (Cleaned Up and Organized) ---
# Core & User Management
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(role.router)
app.include_router(service.router)

# Primary Operations
app.include_router(vehicle.router)
app.include_router(trip.router)
app.include_router(fuel.router)
app.include_router(request.router)
app.include_router(approval.router)

# Maintenance & Repair
app.include_router(maintenance.router)
app.include_router(panne.router)
app.include_router(reparation.router)
app.include_router(garage.router)

# Vehicle & Fuel Categories
app.include_router(vehicle_make.router)
app.include_router(vehicle_model.router)
app.include_router(vehicle_type.router)
app.include_router(vehicle_transmission.router)
app.include_router(fuel_type.router)
app.include_router(category_maintenance.router)
app.include_router(category_panne.router)

# Dashboard & Analytics APIs
app.include_router(dashboard_data_api.router)
app.include_router(analytics_api.router)


# =================================================================
# --- HTML PAGE SERVING ENDPOINTS (Secured by Cookies) ---
# =================================================================

# === PUBLIC PAGES ===
@app.get("/", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_root(request: Request):
    return RedirectResponse(url="/login.html")

@app.get("/login.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# === PROTECTED DASHBOARDS FOR SPECIFIC ROLES ===
@app.get("/user_dashboard.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_user_dashboard(request: Request, user: models.User = Depends(oauth2.require_user_page)):
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "user": user})

@app.get("/driver_dashboard.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_driver_dashboard(request: Request, user: models.User = Depends(oauth2.require_driver_page)):
    return templates.TemplateResponse("driver_dashboard.html", {"request": request, "user": user})

@app.get("/chef_dashboard.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_chef_dashboard(request: Request, user: models.User = Depends(oauth2.require_chef_page)):
    return templates.TemplateResponse("chef_dashboard.html", {"request": request, "user": user})

@app.get("/logistic_dashboard.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_logistic_dashboard(request: Request, user: models.User = Depends(oauth2.require_logistic_page)):
    return templates.TemplateResponse("logistic_dashboard.html", {"request": request, "user": user})

@app.get("/charoi_dashboard.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_charoi_dashboard(request: Request, user: models.User = Depends(oauth2.require_charoi_page)):
    return templates.TemplateResponse("charoi_dashboard.html", {"request": request, "user": user})

# === ADMIN & SUPERADMIN PAGES (All protected by the same dependency) ===

@app.get("/admin_dashboard.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_admin_dashboard(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "user": user})

@app.get("/dashboard.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_superadmin_dashboard(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

# --- Complete set of Admin Navigation Pages (No Duplicates) ---
@app.get("/analytics.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_analytics_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("analytics.html", {"request": request, "user": user})

@app.get("/users.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_users_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("users.html", {"request": request, "user": user})

@app.get("/vehicle.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_vehicle_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("vehicle.html", {"request": request, "user": user})

@app.get("/trip.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_trips_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("trip.html", {"request": request, "user": user})

@app.get("/request.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_requests_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("request.html", {"request": request, "user": user})
    
@app.get("/fuel.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_fuel_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("fuel.html", {"request": request, "user": user})

@app.get("/maintenance.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_maintenance_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("maintenance.html", {"request": request, "user": user})

@app.get("/panne.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_panne_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("panne.html", {"request": request, "user": user})

@app.get("/reparation.html", response_class=HTMLResponse, tags=["Frontend Pages"])
async def serve_reparation_page(request: Request, user: models.User = Depends(oauth2.require_admin_page)):
    return templates.TemplateResponse("reparation.html", {"request": request, "user": user})