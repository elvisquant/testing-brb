# In app/routers/request.py

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, String
from typing import List

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/requests",
    tags=['Requests API']
)

# --- CREATE a new request ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.VehicleRequestOut)
def create_request(
    request_data: schemas.VehicleRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_active_user)
):
    """
    Allows any authenticated user to create a new vehicle request.
    The status is explicitly set to "pending".
    """
    new_request = models.VehicleRequest(
        **request_data.model_dump(), 
        requester_id=current_user.id, 
        status="pending"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

# --- GET all requests (with role-based filtering) ---
# UPDATED FUNCTION STARTS HERE
@router.get("/", response_model=List[schemas.VehicleRequestOut])
def get_all_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_role(["admin", "superadmin", "logistic", "charoi", "chef"])),
    limit: int = 100,
    skip: int = 0
):
    """
    Fetches a list of requests. The data is filtered based on the user's role:
    - Admin/Superadmin: See all requests with no filters.
    - Chef: Sees all requests from their own department.
    - Logistic: Sees all requests with status 'approved_by_chef'.
    - Charoi: Sees all requests with status 'approved_by_logistic'.
    """
    # Start with a base query that includes all necessary related data.
    query = db.query(models.VehicleRequest).options(
        joinedload(models.VehicleRequest.requester).joinedload(models.User.service),
        joinedload(models.VehicleRequest.approvals).joinedload(models.RequestApproval.approver)
    )

    user_role = current_user.role.name.lower() if current_user.role else ""

    # --- APPLY FILTERS BASED ON USER ROLE ---

    if user_role == "chef":
        # Filter by the chef's specific department (service_id).
        user_service_id = current_user.service_id
        if user_service_id is None:
            return []  # A chef with no department sees no requests.
        
        # Join with the User table to filter by the requester's service_id.
        query = query.join(models.User, models.VehicleRequest.requester_id == models.User.id)
        query = query.filter(models.User.service_id == user_service_id)

    elif user_role == "logistic":
        # Filter to show only requests waiting for logistics approval.
        query = query.filter(models.VehicleRequest.status == "approved_by_chef")

    elif user_role == "charoi":
        # Filter to show only requests waiting for charoi approval.
        query = query.filter(models.VehicleRequest.status == "approved_by_logistic")
    
    # NOTE: For 'admin' and 'superadmin', no additional filters are applied,
    # so they will see all requests from the base query.

    # --- FINALIZE AND EXECUTE THE QUERY ---
    
    # Apply ordering, limit, and skip for pagination, then execute.
    requests = query.order_by(models.VehicleRequest.created_at.desc()).limit(limit).offset(skip).all()
    
    return requests
# UPDATED FUNCTION ENDS HERE


# --- GET requests for the currently logged-in user ---
@router.get("/my-requests", response_model=List[schemas.VehicleRequestOut])
def get_my_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_active_user),
    limit: int = 50,
    skip: int = 0
):
    """
    Fetches all requests made by the currently authenticated user.
    """
    requests = (
        db.query(models.VehicleRequest)
        .filter(models.VehicleRequest.requester_id == current_user.id)
        .options(
            joinedload(models.VehicleRequest.requester).joinedload(models.User.service),
            joinedload(models.VehicleRequest.approvals).joinedload(models.RequestApproval.approver)
        )
        .order_by(models.VehicleRequest.created_at.desc())
        .limit(limit)
        .offset(skip)
        .all()
    )
    return requests

# --- GET a specific request by ID ---
@router.get("/{id}", response_model=schemas.VehicleRequestOut)
def get_request_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_active_user)
):
    """
    Fetches a single request by its ID, with authorization checks.
    """
    db_request = (
        db.query(models.VehicleRequest)
        .options(
            joinedload(models.VehicleRequest.requester).joinedload(models.User.service),
            joinedload(models.VehicleRequest.approvals).joinedload(models.RequestApproval.approver)
        )
        .filter(models.VehicleRequest.id == id)
        .first()
    )
    
    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Request with id: {id} not found.")

    user_role = current_user.role.name.lower() if current_user.role and current_user.role.name else ""
    user_service_id = current_user.service_id
    is_privileged_viewer = user_role in ["admin", "superadmin", "logistic", "charoi"]
    is_owner = db_request.requester_id == current_user.id
    is_chef_with_same_service = (
        user_role == "chef" and
        user_service_id is not None and
        db_request.requester and
        db_request.requester.service_id == user_service_id
    )

    if not (is_privileged_viewer or is_owner or is_chef_with_same_service):
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to view this request."
        )

    return db_request

# --- UPDATE request assignment (Admin/Logistics) ---
@router.put("/{id}/assign", response_model=schemas.VehicleRequestOut)
def update_request_assignment(
    id: int,
    assignment_data: schemas.VehicleRequestAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_role(["admin", "superadmin", "charoi", "logistic"]))
):
    """
    Allows privileged users to assign a vehicle and/or driver to a request.
    """
    request_query = db.query(models.VehicleRequest).filter(models.VehicleRequest.id == id)
    db_request = request_query.first()

    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Request with id: {id} not found")

    update_data = assignment_data.model_dump(exclude_unset=True)
    request_query.update(update_data, synchronize_session=False)
    
    db.commit()
    db.refresh(db_request)
    
    return db_request

# --- DELETE a request ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_active_user)
):
    """
    Deletes a request. Only admins or the owner (if still pending) can delete.
    """
    request_query = db.query(models.VehicleRequest).filter(models.VehicleRequest.id == id)
    db_request = request_query.first()
    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Request with id: {id} not found")

    is_admin = current_user.role.name.lower() in ["admin", "superadmin"]
    is_owner = db_request.requester_id == current_user.id
    is_pending = db_request.status.lower() == "pending"

    if is_admin or (is_owner and is_pending):
        request_query.delete(synchronize_session=False)
        db.commit()
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this request")

    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- GET COUNT of pending requests (for Admin dashboards) ---
@router.get("/count/pending", response_model=schemas.PendingRequestsCount)
def get_pending_requests_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_role(["admin", "superadmin", "charoi", "logistic"]))
):
    """
    Gets a count of all requests currently in a 'pending' state.
    """
    pending_count = db.query(models.VehicleRequest).filter(
        func.lower(cast(models.VehicleRequest.status, String)) == 'pending'
    ).count()

    return {"count": pending_count}