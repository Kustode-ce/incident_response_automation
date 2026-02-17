-- Database initialization script for Incident Response Automation
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Grant privileges (database and user are created by POSTGRES_DB and POSTGRES_USER env vars)
-- This is just to ensure the user has all necessary permissions

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Incident Response Automation database initialized successfully';
END $$;
