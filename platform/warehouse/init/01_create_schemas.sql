-- Core warehouse zones created automatically by the official Postgres image
-- when the database volume is initialized for the first time.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS metadata;
