"""
Database models for the Abuse Prevention module.
Uses the existing PostgreSQL database from docker-compose.
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class ImageValidation(Base):
    """
    Stores validation results for each image submitted.
    Tracks all four validation checks and their outcomes.
    """
    __tablename__ = 'image_validations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Image identification
    image_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash
    phash = Column(String(64), nullable=True)  # Perceptual hash for similarity
    
    # Overall result
    is_valid = Column(Boolean, nullable=False, default=False)
    overall_score = Column(Integer, nullable=False, default=0)
    
    # Individual check results
    ai_detection_passed = Column(Boolean, nullable=True)
    ai_detection_score = Column(Float, nullable=True)
    ai_detection_reason = Column(Text, nullable=True)
    
    exif_valid = Column(Boolean, nullable=True)
    exif_timestamp = Column(DateTime, nullable=True)
    exif_age_hours = Column(Float, nullable=True)
    exif_reason = Column(Text, nullable=True)
    
    gps_matched = Column(Boolean, nullable=True)
    gps_distance_km = Column(Float, nullable=True)
    exif_latitude = Column(Float, nullable=True)
    exif_longitude = Column(Float, nullable=True)
    user_latitude = Column(Float, nullable=True)
    user_longitude = Column(Float, nullable=True)
    gps_reason = Column(Text, nullable=True)
    
    web_check_passed = Column(Boolean, nullable=True)
    found_online = Column(Boolean, nullable=True)
    web_check_reason = Column(Text, nullable=True)
    
    # Metadata
    validation_reasons = Column(JSON, nullable=True)  # List of all reasons
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<ImageValidation(id={self.id}, is_valid={self.is_valid}, score={self.overall_score})>"


class KnownImageHash(Base):
    """
    Stores perceptual hashes of all processed images.
    Used to detect if an image has been submitted before or exists in our database.
    """
    __tablename__ = 'known_image_hashes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Hash data
    phash = Column(String(64), nullable=False, index=True)  # Perceptual hash
    sha256_hash = Column(String(64), nullable=False, index=True)  # Full SHA256
    
    # Source information
    source_type = Column(String(50), nullable=False, default='submission')  # submission, web, known_fake
    source_url = Column(Text, nullable=True)  # If from web
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<KnownImageHash(id={self.id}, source={self.source_type})>"


# SQL for creating tables (for raw psycopg2 usage)
CREATE_TABLES_SQL = """
-- Image validations table
CREATE TABLE IF NOT EXISTS image_validations (
    id SERIAL PRIMARY KEY,
    image_hash VARCHAR(64) NOT NULL,
    phash VARCHAR(64),
    is_valid BOOLEAN NOT NULL DEFAULT FALSE,
    overall_score INTEGER NOT NULL DEFAULT 0,
    
    ai_detection_passed BOOLEAN,
    ai_detection_score FLOAT,
    ai_detection_reason TEXT,
    
    exif_valid BOOLEAN,
    exif_timestamp TIMESTAMP,
    exif_age_hours FLOAT,
    exif_reason TEXT,
    
    gps_matched BOOLEAN,
    gps_distance_km FLOAT,
    exif_latitude FLOAT,
    exif_longitude FLOAT,
    user_latitude FLOAT,
    user_longitude FLOAT,
    gps_reason TEXT,
    
    web_check_passed BOOLEAN,
    found_online BOOLEAN,
    web_check_reason TEXT,
    
    validation_reasons JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_image_validations_hash ON image_validations(image_hash);
CREATE INDEX IF NOT EXISTS idx_image_validations_phash ON image_validations(phash);

-- Known image hashes table
CREATE TABLE IF NOT EXISTS known_image_hashes (
    id SERIAL PRIMARY KEY,
    phash VARCHAR(64) NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'submission',
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_known_hashes_phash ON known_image_hashes(phash);
CREATE INDEX IF NOT EXISTS idx_known_hashes_sha256 ON known_image_hashes(sha256_hash);
"""


def create_tables(connection):
    """
    Create the abuse prevention tables using a raw psycopg2 connection.
    
    Args:
        connection: psycopg2 database connection
    """
    cursor = connection.cursor()
    cursor.execute(CREATE_TABLES_SQL)
    connection.commit()
    cursor.close()
