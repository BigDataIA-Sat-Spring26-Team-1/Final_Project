CREATE DATABASE IF NOT EXISTS CURATE_AI;
USE DATABASE CURATE_AI;

CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS user_personas (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    linkedin_url VARCHAR(2000),
    job_title VARCHAR(255),
    seniority VARCHAR(100),
    persona_archetype VARCHAR(100), 
    bio_summary TEXT, 
    explicit_category_weights VARIANT,
    behavioral_category_weights VARIANT, 
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS article_clusters (
    id VARCHAR(36) PRIMARY KEY,
    primary_title VARCHAR(500) NOT NULL,
    primary_summary TEXT,
    synthesized_content TEXT, 
    category_weights VARIANT, 
    trend_status VARCHAR(50), 
    cluster_size INTEGER DEFAULT 1,
    social_popularity_score FLOAT DEFAULT 0.0,
    final_trend_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS articles_raw (
    id VARCHAR(36) PRIMARY KEY,
    cluster_id VARCHAR(36) REFERENCES article_clusters(id), 
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50), 
    title VARCHAR(500) NOT NULL,
    url VARCHAR(2000) NOT NULL,
    summary TEXT,
    content_raw VARIANT, 
    extracted_full_text TEXT, 
    source_tags VARIANT, 
    internal_category_weights VARIANT, 
    published_at TIMESTAMP_NTZ, 
    fetched_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() 
);

CREATE TABLE IF NOT EXISTS daily_selections (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    cluster_id VARCHAR(36) NOT NULL REFERENCES article_clusters(id),
    selection_type VARCHAR(50), 
    match_score FLOAT NOT NULL, 
    selected_date DATE NOT NULL,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS newsletters (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    edition_date DATE NOT NULL,
    draft_metadata VARIANT, 
    draft_content TEXT, 
    final_content TEXT, 
    status VARCHAR(50) DEFAULT 'DRAFT', 
    feedback_signal VARCHAR(50), 
    execution_path_taken VARCHAR(500), 
    generated_at TIMESTAMP_NTZ, 
    
    sent_at TIMESTAMP_NTZ,
    delivery_status VARCHAR(50), 
    delivery_message_id VARCHAR(255), 
    delivery_recipient VARCHAR(255), 
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    industry VARCHAR(255),
    description TEXT,
    company_size VARCHAR(50), 
    created_by VARCHAR(36), 
    authority_vectors VARIANT, 
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS content_briefs (
    id VARCHAR(36) PRIMARY KEY,
    company_id VARCHAR(36) NOT NULL REFERENCES companies(id),
    cluster_id VARCHAR(36) REFERENCES article_clusters(id), 
    brief_content TEXT, 
    urgency_tier VARCHAR(50), 
    strategic_angle TEXT,
    target_keywords VARIANT, 
    structured_brief VARIANT, 
    status VARCHAR(50) DEFAULT 'GENERATED',
    generated_at TIMESTAMP_NTZ, 
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

ALTER TABLE newsletters ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP_NTZ;
ALTER TABLE newsletters ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(50);
ALTER TABLE newsletters ADD COLUMN IF NOT EXISTS delivery_message_id VARCHAR(255);
ALTER TABLE newsletters ADD COLUMN IF NOT EXISTS delivery_recipient VARCHAR(255);

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'USER';
ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id VARCHAR(36);

ALTER TABLE companies ADD COLUMN IF NOT EXISTS target_audience TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS key_products TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS content_pillars TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS competitors TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS tone_of_voice VARCHAR(50);

ALTER TABLE companies ADD COLUMN IF NOT EXISTS content_affinity_weights VARIANT;