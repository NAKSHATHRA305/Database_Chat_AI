import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(root_path="/api")

# app.py
import os
import io
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pymongo import MongoClient
import pandas as pd
import openai
from sqlalchemy.orm import Session

from db_config import get_db, User, DatabaseDesign

# Load environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

if not OPENAI_API_KEY or not MONGO_URI:
    raise RuntimeError("OPENAI_API_KEY or MONGO_URI is not set in environment variables.")

# OpenAI setup
openai.api_key = OPENAI_API_KEY

# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client.get_database("canopy_users")
users_collection = mongo_db["users"]

# FastAPI setup
app = FastAPI(title="Canopy DB AI Designer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------
# Helper Functions
# ---------------------
def get_user_from_mongo(email: str):
    user = users_collection.find_one({"email": email})
    return user

# ---------------------
# Routes
# ---------------------

@app.post("/register")
def register_user(name: str, email: str, password: str):
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="User already exists")
    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": password,
        "created_at": datetime.utcnow()
    })
    return {"message": "User registered successfully"}

@app.post("/login")
def login_user(email: str, password: str):
    user = users_collection.find_one({"email": email})
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "user": {"name": user["name"], "email": user["email"]}}

@app.post("/ai/design")
def generate_design(prompt: str, email: str, db: Session = Depends(get_db)):
    user = get_user_from_mongo(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # OpenAI API call
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Generate a database design for: {prompt}"}]
        )
        design_json = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {e}")

    # Save to PostgreSQL
    db_design = DatabaseDesign(
        user_id=None,  # Optional: link to PostgreSQL user if needed
        prompt=prompt,
        design_json=design_json
    )
    db.add(db_design)
    db.commit()
    db.refresh(db_design)

    return {"design_id": db_design.id, "design_json": design_json}

@app.post("/upload_excel/{design_id}")
def upload_excel(design_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    design = db.query(DatabaseDesign).filter(DatabaseDesign.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    content = file.file.read()
    design.excel_data = content
    db.commit()
    return {"message": "Excel file uploaded successfully"}

@app.get("/download_excel/{design_id}")
def download_excel(design_id: int, db: Session = Depends(get_db)):
    design = db.query(DatabaseDesign).filter(DatabaseDesign.id == design_id).first()
    if not design or not design.excel_data:
        raise HTTPException(status_code=404, detail="Excel file not found")

    return StreamingResponse(io.BytesIO(design.excel_data),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename=design_{design_id}.xlsx"})
