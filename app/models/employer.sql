-- Add to app/models/schema.sql
-- Employers Table - extends user functionality for employer-specific data

CREATE TABLE IF NOT EXISTS employers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    company_description TEXT,
    industry TEXT,
    company_size TEXT, -- 'startup', 'small', 'medium', 'large', 'enterprise'
    website TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    zip_code TEXT,
    profile_url TEXT,
    logo_url TEXT,
    linkedin_company_url TEXT,
    founded_year INTEGER,
    company_type TEXT DEFAULT 'private', -- 'private', 'public', 'nonprofit', 'government'
    registration_number TEXT,
    tax_id TEXT,
    location TEXT,
    headquarters TEXT,
    
    -- Employer-specific settings
    is_verified BOOLEAN DEFAULT FALSE,
    verification_date TIMESTAMP,
    verified_by INTEGER,
    subscription_plan TEXT DEFAULT 'basic', -- 'basic', 'premium', 'enterprise'
    subscription_expires_at TIMESTAMP,
    
    -- Job posting limits based on subscription
    monthly_job_limit INTEGER DEFAULT 20,
    jobs_posted_this_month INTEGER DEFAULT 0,
    
    -- Contact person details (if different from user)
    contact_person_name TEXT,
    contact_person_email TEXT,
    contact_person_phone TEXT,
    contact_person_position TEXT,
    
    -- Features and permissions
    can_post_jobs BOOLEAN DEFAULT TRUE,
    can_view_applications BOOLEAN DEFAULT TRUE,
    can_message_candidates BOOLEAN DEFAULT TRUE,
    can_access_analytics BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT, -- Internal admin notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    email_verification_token TEXT,
    email_verification_token_expires TEXT,

    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    CHECK (company_size IN ('startup', 'small', 'medium', 'large', 'enterprise')),
    CHECK (company_type IN ('private', 'public', 'nonprofit', 'government')),
    CHECK (subscription_plan IN ('basic', 'premium', 'enterprise')),
    CHECK (founded_year IS NULL OR founded_year > 1800),
    CHECK (monthly_job_limit >= 0),
    CHECK (jobs_posted_this_month >= 0),
    CHECK (LENGTH(company_name) >= 2)
);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token);

-- Employer Documents Table (for storing verification documents)
CREATE TABLE IF NOT EXISTS employer_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER NOT NULL,
    document_type TEXT NOT NULL, -- 'business_license', 'tax_certificate', 'incorporation_docs', 'other'
    file_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    verified_by INTEGER,
    notes TEXT,
    
    FOREIGN KEY (employer_id) REFERENCES employers(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL,
    
    CHECK (document_type IN ('business_license', 'tax_certificate', 'incorporation_docs', 'other')),
    CHECK (file_size > 0)
);

-- Employer Reviews/Ratings Table (for candidate feedback)
CREATE TABLE IF NOT EXISTS employer_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    job_id INTEGER, -- Optional: specific job the review relates to
    rating INTEGER NOT NULL, -- 1-5 stars
    title TEXT,
    review_text TEXT,
    pros TEXT,
    cons TEXT,
    is_anonymous BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by INTEGER,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (employer_id) REFERENCES employers(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    
    CHECK (rating >= 1 AND rating <= 5),
    
    UNIQUE(employer_id, reviewer_id, job_id) -- Prevent duplicate reviews
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_employers_user_id ON employers(user_id);
CREATE INDEX IF NOT EXISTS idx_employers_company_name ON employers(company_name);
CREATE INDEX IF NOT EXISTS idx_employers_industry ON employers(industry);
CREATE INDEX IF NOT EXISTS idx_employers_city ON employers(city);
CREATE INDEX IF NOT EXISTS idx_employers_is_verified ON employers(is_verified);
CREATE INDEX IF NOT EXISTS idx_employers_is_active ON employers(is_active);
CREATE INDEX IF NOT EXISTS idx_employers_subscription_plan ON employers(subscription_plan);
CREATE INDEX IF NOT EXISTS idx_employers_created_at ON employers(created_at);

CREATE INDEX IF NOT EXISTS idx_employer_documents_employer_id ON employer_documents(employer_id);
CREATE INDEX IF NOT EXISTS idx_employer_documents_document_type ON employer_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_employer_documents_verified ON employer_documents(verified);

CREATE INDEX IF NOT EXISTS idx_employer_reviews_employer_id ON employer_reviews(employer_id);
CREATE INDEX IF NOT EXISTS idx_employer_reviews_reviewer_id ON employer_reviews(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_employer_reviews_rating ON employer_reviews(rating);
CREATE INDEX IF NOT EXISTS idx_employer_reviews_is_approved ON employer_reviews(is_approved);

-- Update jobs table to link with employers table
-- Add employer_id to jobs table if not already present
-- ALTER TABLE jobs ADD COLUMN employer_id INTEGER REFERENCES employers(id) ON DELETE SET NULL;