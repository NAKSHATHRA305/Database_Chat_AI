import os
import io
import json
import re
import uvicorn
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from bson import ObjectId
from pymongo import MongoClient
from openai import OpenAI
from dotenv import load_dotenv
from db_config import engine, SessionLocal, ExcelData
import pandas as pd

# ---------- Load environment ----------
load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# ---------- Initialize OpenAI ----------
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
if not openai_client:
    print("⚠️ OpenAI API key not set - AI features will not work")

# ---------- Initialize MongoDB ----------
try:
    client = MongoClient(MONGO_URI)
    client.admin.command("ping")
    db = client["canopy_db"]
    users_col = db["users"]
    messages_col = db["messages"]
    sessions_col = db["sessions"]
    conversations_col = db["conversations"]
    database_designs_col = db["database_designs"]
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    client = None

# ---------- Initialize FastAPI ----------
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- AI Helpers ----------
def extract_json_from_response(text: str):
    """Extract JSON from OpenAI response, handling markdown code blocks."""
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Try to find raw JSON
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return text

async def generate_database_design(prompt: str, user_id: str):
    """Generate database design using OpenAI or fallback demo mode."""
    if not openai_client:
        return generate_demo_database_design(prompt, user_id)
    
    try:
        system_prompt = """You are a database design expert. Generate a database schema in JSON format.

IMPORTANT: 
1. Return ONLY valid JSON without any markdown formatting or code blocks.
2. Use EXACT column names as mentioned by the user - do NOT add or modify column names
3. Do NOT add extra columns like 'created_at' or 'updated_at' unless explicitly requested

The JSON structure must be:
{
    "database_name": "Name of the database",
    "description": "Brief description",
    "tables": [
        {
            "table_name": "table_name",
            "description": "Table description",
            "columns": [
                {
                    "column_name": "exact_column_name_from_user",
                    "data_type": "VARCHAR(100) or INT or DATE etc",
                    "description": "Column purpose"
                }
            ]
        }
    ]
}

Rules:
1. Use ONLY the column names specified by the user - do not add extra columns
2. Preserve exact spelling, capitalization, and naming from user's prompt
3. If no specific data types are mentioned, use sensible defaults (VARCHAR(100) for text, INT for numbers, DECIMAL for price/money, DATE for dates)
4. Return ONLY the JSON object, no explanations or markdown"""

        user_prompt = f"Create a database design with EXACT column names as specified: {prompt}"
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        json_str = extract_json_from_response(ai_response)
        
        try:
            design_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw response: {ai_response}")
            # Fall back to demo mode if JSON parsing fails
            return generate_demo_database_design(prompt, user_id)

        # Validate structure
        if not isinstance(design_data, dict) or 'tables' not in design_data:
            print(f"Invalid structure in AI response: {design_data}")
            return generate_demo_database_design(prompt, user_id)

        # Store in MongoDB
        design_doc = {
            "user_id": user_id,
            "prompt": prompt,
            "design": design_data,
            "created_at": datetime.now(timezone.utc),
            "ai_response": ai_response,
        }
        result = database_designs_col.insert_one(design_doc)
        design_doc["_id"] = str(result.inserted_id)
        
        return {
            "success": True, 
            "design": design_data, 
            "design_id": str(result.inserted_id)
        }

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return generate_demo_database_design(prompt, user_id)


def generate_demo_database_design(prompt: str, user_id: str):
    """Fallback database design - extracts EXACT column names from user prompt."""
    prompt_lower = prompt.lower()
    
    # Try to extract table name
    table_name = "custom_table"
    table_match = re.search(r'(?:create|make|build)\s+(?:a\s+)?(\w+)\s+table', prompt_lower)
    if table_match:
        table_name = table_match.group(1)
    
    # Extract column names - look for common patterns
    columns = []
    
    # Pattern 1: "with column1, column2, column3"
    with_match = re.search(r'with\s+([\w\s,]+?)(?:\.|$|and\s+\w+\s+(?:as|for))', prompt_lower)
    if with_match:
        cols_str = with_match.group(1)
        # Split by comma or 'and'
        cols = re.split(r',|\s+and\s+', cols_str)
        columns = [col.strip() for col in cols if col.strip()]
    
    # If no columns found, try to extract any words that look like column names
    if not columns:
        # Remove common words and extract potential column names
        words = prompt.split()
        skip_words = {'create', 'make', 'table', 'with', 'a', 'an', 'the', 'for', 'and', 'database'}
        potential_cols = [w.strip('.,!?;:()') for w in words if w.lower() not in skip_words and len(w) > 2]
        if len(potential_cols) > 1:
            columns = potential_cols[1:]  # Skip first word (likely table name)
    
    # If still no columns, use defaults
    if not columns:
        columns = ["id", "name"]
    
    # Create column definitions with appropriate data types
    column_defs = []
    for col in columns:
        col_lower = col.lower()
        
        # Determine data type based on column name
        if col_lower == "id":
            data_type = "INT PRIMARY KEY AUTO_INCREMENT"
        elif "date" in col_lower or "time" in col_lower:
            data_type = "DATETIME"
        elif "age" in col_lower or "count" in col_lower or "quantity" in col_lower:
            data_type = "INT"
        elif "email" in col_lower:
            data_type = "VARCHAR(255)"
        elif "price" in col_lower or "amount" in col_lower or "cost" in col_lower or "salary" in col_lower:
            data_type = "DECIMAL(10,2)"
        elif "phone" in col_lower:
            data_type = "VARCHAR(20)"
        elif "description" in col_lower or "address" in col_lower:
            data_type = "TEXT"
        else:
            data_type = "VARCHAR(100)"
        
        column_defs.append({
            "column_name": col,  # Keep exact column name from user
            "data_type": data_type,
            "description": f"{col.replace('_', ' ').title()} field"
        })
    
    design_data = {
        "database_name": f"{table_name.replace('_', ' ').title()} Database",
        "description": f"Database for {table_name} based on your prompt",
        "tables": [{
            "table_name": table_name,
            "description": f"Main {table_name} table",
            "columns": column_defs
        }],
    }
    
    # Store in MongoDB
    design_doc = {
        "user_id": user_id,
        "prompt": prompt,
        "design": design_data,
        "created_at": datetime.now(timezone.utc),
        "ai_response": f"Demo mode: {design_data['database_name']} generated based on your prompt: {prompt}",
    }
    result = database_designs_col.insert_one(design_doc)
    design_doc["_id"] = str(result.inserted_id)
    
    return {
        "success": True, 
        "design": design_data, 
        "design_id": str(result.inserted_id)
    }

# ---------- API Routes ----------
@app.get("/api/hello")
def read_root():
    return {"message": "Backend is working!"}


@app.post("/api/ai/design")
async def ai_database_design(payload: dict):
    if not payload or "prompt" not in payload or "user_id" not in payload:
        raise HTTPException(status_code=400, detail="Prompt and user_id required")
    result = await generate_database_design(payload["prompt"], payload["user_id"])
    status = 200 if result.get("success") else 400
    return JSONResponse(content=result, status_code=status)


@app.post("/api/register")
def register_user(payload: dict):
    if not payload or "name" not in payload or "email" not in payload:
        raise HTTPException(status_code=400, detail="Name and email required")
    existing_user = users_col.find_one({"email": payload["email"]})
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_data = {
        "name": payload["name"], 
        "email": payload["email"], 
        "created_at": datetime.now(timezone.utc), 
        "last_login": datetime.now(timezone.utc)
    }
    result = users_col.insert_one(user_data)
    return {
        "status": "success", 
        "user": {
            "id": str(result.inserted_id), 
            "name": user_data["name"], 
            "email": user_data["email"]
        }
    }


@app.post("/api/login")
def login_user(payload: dict):
    if not payload or "email" not in payload:
        raise HTTPException(status_code=400, detail="Email required")
    user = users_col.find_one({"email": payload["email"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    current_time = datetime.now(timezone.utc)
    users_col.update_one({"_id": user["_id"]}, {"$set": {"last_login": current_time}})
    # Log activity
    db["login_activity"].insert_one({
        "user_id": str(user["_id"]), 
        "email": user["email"], 
        "name": user["name"], 
        "timestamp": current_time, 
        "action": "login"
    })
    return {
        "status": "success", 
        "user": {
            "id": str(user["_id"]), 
            "name": user["name"], 
            "email": user["email"]
        }
    }


@app.get("/api/designs/{user_id}")
def get_user_designs(user_id: str):
    designs = list(database_designs_col.find({"user_id": user_id}))
    for d in designs:
        d["_id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat()
    return designs


@app.get("/api/excel/{design_id}")
def get_design(design_id: str):
    """Fetch a design by ID for the Excel editor."""
    try:
        design = database_designs_col.find_one({"_id": ObjectId(design_id)})
        if not design:
            raise HTTPException(status_code=404, detail="Design not found")
        design["_id"] = str(design["_id"])
        if "created_at" in design:
            design["created_at"] = design["created_at"].isoformat()
        return design
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching design: {str(e)}")


# ---------- Excel / PostgreSQL Routes ----------
@app.post("/api/excel/{design_id}/save")
def save_excel(design_id: str, payload: dict):
    """Save final Excel-like data into PostgreSQL using ORM."""
    user_id = payload.get("user_id")
    design_data = payload.get("design_data")
    
    if not design_data:
        raise HTTPException(status_code=400, detail="design_data is required")
    
    session = SessionLocal()
    try:
        # Create ExcelData record
        record = ExcelData(
            user_id=user_id or "unknown",
            table_name=f"design_{design_id}",
            schema={"columns": list(design_data[0].keys())} if design_data else {},
            data=design_data,
        )
        session.add(record)
        session.commit()
        return {"success": True, "message": "Data saved to PostgreSQL via ORM"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save to PostgreSQL: {str(e)}")
    finally:
        session.close()


# ---------- Serve Static Frontend ----------
DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")


@app.get("/", response_class=HTMLResponse)
def serve_root():
    login_file = os.path.join(DIST_DIR, "login.html")
    if os.path.isfile(login_file):
        return FileResponse(login_file)
    # Fallback to index.html
    index_file = os.path.join(DIST_DIR, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Frontend not built. Run 'npm run build' in frontend directory</h1>", status_code=404)


# ---------- Run ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

