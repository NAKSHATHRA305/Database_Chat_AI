"""
PostgreSQL Models for Canopy DB
Defines the ExcelData model for storing spreadsheet data
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ExcelData(Base):
    """
    Model to store Excel/Spreadsheet data in PostgreSQL
    """
    __tablename__ = "excel_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True)
    table_name = Column(String(255), nullable=False)
    schema = Column(JSON, nullable=True)  # Store column definitions as JSON
    data = Column(JSON, nullable=False)   # Store the actual spreadsheet data as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ExcelData(id={self.id}, table_name='{self.table_name}', user_id='{self.user_id}')>"