"""
PostgreSQL database configuration for Canopy DB
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from models import ExcelData  # Import the ExcelData model

# PostgreSQL connection string
def is_docker():
    try:
        with open('/proc/1/cgroup', 'rt') as f:
            return 'docker' in f.read()
    except Exception:
        return False

host = "postgres" if is_docker() else "localhost"

POSTGRES_URI = os.environ.get(
    "POSTGRES_URI",
    f"postgresql://postgres:1234@{host}:5432/canopy_db"
)

# Create SQLAlchemy engine and session
try:
    engine = create_engine(POSTGRES_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    print("✅ Successfully connected to PostgreSQL!")
except Exception as e:
    print(f"❌ Failed to connect to PostgreSQL: {e}")
    print("Please check your POSTGRES_URI environment variable")
    engine = None
    SessionLocal = None
    Base = None

# Define PostgreSQL models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    designs = relationship("DatabaseDesign", back_populates="user")
    login_activities = relationship("LoginActivity", back_populates="user")

class DatabaseDesign(Base):
    __tablename__ = "database_designs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    prompt = Column(Text, nullable=False)
    design_json = Column(Text, nullable=False)  # Store the JSON design
    excel_data = Column(LargeBinary)  # Store the Excel file as binary
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="designs")

class LoginActivity(Base):
    __tablename__ = "login_activity"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    email = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(50), default="login")
    
    # Relationships
    user = relationship("User", back_populates="login_activities")

# Create tables if they don't exist
if engine:
    Base.metadata.create_all(bind=engine)
    # Also create ExcelData table
    from models import Base as ModelsBase
    ModelsBase.metadata.create_all(bind=engine)

# Helper function to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()