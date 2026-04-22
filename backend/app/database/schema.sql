-- Database definitions for CurateAI v1

CREATE DATABASE IF NOT EXISTS CURATE_AI;
USE DATABASE CURATE_AI;

-- Ensure public schema exists
CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

--------------------------------------------------------
-- Core Entities
--------------------------------------------------------

-- 1. Users Table
-- Stores the base login and identity credentials
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 2. User Personas (Cold-start + Behavioral Refinement)
-- Maintained separately from `users` to cleanly track the evolving behavioral models and PDF-extracted metadata.
CREATE TABLE IF NOT EXISTS user_personas (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    linkedin_url VARCHAR(2000),
    job_title VARCHAR(255),
    seniority VARCHAR(100),
    persona_archetype VARCHAR(100), -- Classification into 5-7 core archetypes for scaled caching
    bio_summary TEXT, -- LLM extracted bio summarizing their professional background
    explicit_category_weights VARIANT, -- Weights declared initially or extracted at onboarding
    behavioral_category_weights VARIANT, -- Weights dynamically adjusted via weekly feedback loops
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

--------------------------------------------------------
-- Content Ingestion & Intelligence Pipeline
--------------------------------------------------------

-- 3. Article Clusters (Deduplicated Main Entities)
-- Represents the synthesized conceptual "story" spanning multiple raw articles (the output of Semantic Dedup DAG).
CREATE TABLE IF NOT EXISTS article_clusters (
    id VARCHAR(36) PRIMARY KEY,
    primary_title VARCHAR(500) NOT NULL,
    primary_summary TEXT,
    synthesized_content TEXT, -- Cleaned content post-deduplication
    category_weights VARIANT, -- Multi-label LLM tags dynamically applied to this specific event
    trend_status VARCHAR(50), -- e.g., 'BREAKING', 'TRENDING', 'COMMUNITY-PICK'
    cluster_size INTEGER DEFAULT 1,
    social_popularity_score FLOAT DEFAULT 0.0,
    final_trend_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 4. Articles Raw (The Ingestion Feed)
-- The daily raw extracted RSS feed/Reddit posts. Ties backwards to `article_clusters` once pipeline evaluates them.
CREATE TABLE IF NOT EXISTS articles_raw (
    id VARCHAR(36) PRIMARY KEY,
    cluster_id VARCHAR(36) REFERENCES article_clusters(id), -- Nullable initially, assigned during deduplication
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50), -- e.g., 'RSS', 'Reddit', 'HackerNews'
    title VARCHAR(500) NOT NULL,
    url VARCHAR(2000) NOT NULL,
    summary TEXT,
    content_raw VARIANT, -- JSON dump of the raw unstructured payload
    extracted_full_text TEXT, -- Explicit text payload parsed via trafilatura
    source_tags VARIANT, -- Optional raw tags straight from the RSS feed provider
    internal_category_weights VARIANT, -- AI-generated taxonomy weights for P2 article intelligence
    published_at TIMESTAMP_NTZ, -- Time defined by the content's author
    fetched_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() -- Ingestion pipeline timestamp
);

--------------------------------------------------------
-- Personalization & Generation (B2C)
--------------------------------------------------------

-- 5. Daily Selections
-- Traces which clusters were explicitly selected for which user on a given day to allow pipeline auditing without viewing raw HTML.
CREATE TABLE IF NOT EXISTS daily_selections (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    cluster_id VARCHAR(36) NOT NULL REFERENCES article_clusters(id),
    selection_type VARCHAR(50), -- 'GLOBAL_HIGHLIGHT' vs 'NICHE_GEM' (Dual-layer approach)
    match_score FLOAT NOT NULL, -- P3 Composite score (vector + overlap + trend)
    selected_date DATE NOT NULL,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 6. Newsletters (Final User Deliverables)
-- Contains the actual drafted text from the Writer/Editor agents, plus required HITL states and user signals.
CREATE TABLE IF NOT EXISTS newsletters (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    edition_date DATE NOT NULL,
    draft_metadata VARIANT, -- Internal citations array, rigorous editor notes, LangGraph agent thoughts
    draft_content TEXT, -- Pre-HITL review Markdown content
    final_content TEXT, -- Post-HITL approved clean HTML
    status VARCHAR(50) DEFAULT 'DRAFT', -- Transitions to 'NEEDS_REVISION', 'APPROVED', 'PUBLISHED'
    feedback_signal VARCHAR(50), -- 'THUMBS_UP', 'THUMBS_DOWN' -> feeds back into `behavioral_category_weights`
    execution_path_taken VARCHAR(500), -- LangGraph node trace for observability / debugging
    generated_at TIMESTAMP_NTZ, -- When the draft was produced by the agent
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

--------------------------------------------------------
-- B2B SEO Intelligence Features
--------------------------------------------------------

-- 7. Companies (B2B Client Definitions)
-- Defines the client profiles for the SEO Intelligence agents mapping trends to business offerings.
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    industry VARCHAR(255),
    description TEXT,
    company_size VARCHAR(50), -- e.g., '1-10', '11-50', '51-200', '201-1000', '1000+'
    created_by VARCHAR(36), -- The admin user who provisioned this tenant
    authority_vectors VARIANT, -- Persistent stored vectors representing the company's domain expertise for Cosine mapping
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 8. Content Briefs (Generated SEO Assets)
-- Output of the SEO Opportunity Agent processing 'SURGING' entities.
CREATE TABLE IF NOT EXISTS content_briefs (
    id VARCHAR(36) PRIMARY KEY,
    company_id VARCHAR(36) NOT NULL REFERENCES companies(id),
    cluster_id VARCHAR(36) REFERENCES article_clusters(id), -- Nullable: stand-alone briefs aren't always tied to a specific cluster
    brief_date DATE, -- Business-day the brief addresses
    brief_content TEXT, -- Markdown body rendered by the B2B agent
    urgency_tier VARCHAR(50), -- Output from the 4-signal algorithm: 'HIDDEN_GEM', 'ACT_NOW', 'MONITOR', 'SKIP'
    strategic_angle TEXT,
    target_keywords VARIANT, -- Extracted SpaCy NER outputs / matched opportunities
    structured_brief VARIANT, -- The Pydantic structured output array mapping Titles, Content Blocks, Internal Links
    status VARCHAR(50) DEFAULT 'GENERATED',
    generated_at TIMESTAMP_NTZ, -- When the agent last produced this brief
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
