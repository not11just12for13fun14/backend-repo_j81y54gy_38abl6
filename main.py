import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import TeamMember, Complaint

app = FastAPI(title="Internet Complaints Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Helpers ---------

def collection(name: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    return db[name]

# Seed admin credentials in env for demo
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "opengreen")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ali12345")

# --------- Auth Models ---------
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    role: str
    username: str

# --------- Team Management (by admin) ---------
class TeamCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None

# --------- Complaint Models ---------
class ComplaintCreate(BaseModel):
    title: str
    description: str
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    assigned_to: Optional[str] = None

class NoteCreate(BaseModel):
    text: str

# --------- Routes ---------
@app.get("/")
def root():
    return {"service": "Complaints Tracker API", "admin_hint": {"user": ADMIN_USERNAME, "pass": ADMIN_PASSWORD}}

@app.get("/test")
def test_database():
    resp = {
        "backend": "running",
        "database": "not connected",
        "collections": []
    }
    try:
        if db is not None:
            resp["database"] = "connected"
            resp["collections"] = db.list_collection_names()
    except Exception as e:
        resp["database"] = f"error: {e}"
    return resp

@app.post("/auth/admin", response_model=LoginResponse)
def admin_login(payload: LoginRequest):
    if payload.username == ADMIN_USERNAME and payload.password == ADMIN_PASSWORD:
        return {"role": "admin", "username": ADMIN_USERNAME}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/team", response_model=LoginResponse)
def team_login(payload: LoginRequest):
    coll = collection("teammember")
    user = coll.find_one({"username": payload.username, "password": payload.password, "is_active": True})
    if user:
        return {"role": "team", "username": user["username"]}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Admin creates team member accounts
@app.post("/admin/team")
def create_team_member(data: TeamCreate):
    coll = collection("teammember")
    if coll.find_one({"username": data.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    member = TeamMember(username=data.username, password=data.password, full_name=data.full_name)
    _id = create_document("teammember", member)
    return {"id": _id}

@app.get("/admin/team")
def list_team():
    members = get_documents("teammember")
    for m in members:
        m["_id"] = str(m["_id"])
    return members

# Admin creates complaints and assigns
@app.post("/admin/complaints")
def create_complaint(data: ComplaintCreate):
    comp = Complaint(
        title=data.title,
        description=data.description,
        customer_name=data.customer_name,
        customer_contact=data.customer_contact,
        assigned_to=data.assigned_to,
    )
    _id = create_document("complaint", comp)
    return {"id": _id}

@app.get("/admin/complaints")
def list_complaints(assigned_to: Optional[str] = None):
    query = {"assigned_to": assigned_to} if assigned_to else {}
    items = get_documents("complaint", query)
    for i in items:
        i["_id"] = str(i["_id"])
    return items

# Team endpoints
@app.get("/team/complaints")
def team_my_complaints(username: str):
    items = get_documents("complaint", {"assigned_to": username})
    for i in items:
        i["_id"] = str(i["_id"])
    return items

class StatusUpdate(BaseModel):
    status: str

@app.post("/team/complaints/{complaint_id}/status")
def update_status(complaint_id: str, data: StatusUpdate):
    allowed = {"pending", "progress", "complete", "critical", "hold", "cancelled"}
    if data.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    coll = collection("complaint")
    res = coll.update_one({"_id": ObjectId(complaint_id)}, {"$set": {"status": data.status, "updated_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"ok": True}

@app.post("/team/complaints/{complaint_id}/notes")
def add_note(complaint_id: str, data: NoteCreate, username: Optional[str] = None):
    note = {
        "username": username,
        "text": data.text,
        "timestamp": datetime.now(timezone.utc)
    }
    coll = collection("complaint")
    res = coll.update_one({"_id": ObjectId(complaint_id)}, {"$push": {"notes": note}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
