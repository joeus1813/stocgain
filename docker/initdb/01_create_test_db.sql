-- File: docker/initdb/01_create_test_db.sql
-- Purpose: Create the isolated test database on first volume initialization.
-- Grain: one database.
-- Constructs: CREATE DATABASE.
-- Business question: Where can integration tests run without changing demo data?
CREATE DATABASE stocksense_test;
