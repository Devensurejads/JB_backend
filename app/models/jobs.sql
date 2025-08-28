-- Add to app/models/schema.sql
-- Jobs Management Tables

-- Job Categories Table (for organizing jobs)

CREATE TABLE IF NOT EXISTS job_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT,
    updated_at TEXT
);

-- Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER NOT NULL,
    category_id INTEGER,
    
    -- Basic Job Information
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    short_description TEXT,
    requirements TEXT,
    responsibilities TEXT,
    benefits TEXT,
    department TEXT,
    company_name TEXT,

    company_logo_filename TEXT,
    company_logo_path TEXT,
    company_logo_size INTEGER,
    company_logo_uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Job Details
    employment_type TEXT NOT NULL, -- 'full-time', 'part-time', 'contract', 'freelance', 'internship'
    experience_level TEXT, -- 'entry', 'junior', 'mid', 'senior', 'executive'
    education_level TEXT, -- 'high_school', 'associate', 'bachelor', 'master', 'phd', 'none'
    
    -- Location Information
    location TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    is_remote BOOLEAN DEFAULT FALSE,
    remote_type TEXT, -- 'fully_remote', 'hybrid', 'onsite'
    pincode INTEGER,
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    
    -- Compensation
    salary_min DECIMAL(10, 2),
    salary_max DECIMAL(10, 2),
    salary_currency TEXT DEFAULT 'USD',
    salary_type TEXT DEFAULT 'annual', -- 'hourly', 'daily', 'weekly', 'monthly', 'annual'
    show_salary BOOLEAN DEFAULT TRUE,
    
    -- Job Status and Settings
    status TEXT DEFAULT 'draft', -- 'draft', 'active', 'paused', 'closed', 'expired'
    priority TEXT DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    is_featured BOOLEAN DEFAULT FALSE,
    is_urgent BOOLEAN DEFAULT FALSE,
    
    -- Application Settings
    application_deadline DATE,
    max_applications INTEGER,
    applications_count INTEGER DEFAULT 0,
    auto_close_after_deadline BOOLEAN DEFAULT TRUE,
    
    -- Contact Information
    contact_email TEXT,
    contact_phone TEXT,
    contact_person TEXT,
    application_method TEXT DEFAULT 'internal', -- 'internal', 'external', 'email'
    external_url TEXT, -- For external applications
    
    -- Skills and Requirements
    required_skills TEXT, -- JSON array of required skills
    preferred_skills TEXT, -- JSON array of preferred skills
    languages TEXT, -- JSON array of required languages
    
    -- Additional Information
    company_overview TEXT,
    work_environment TEXT,
    growth_opportunities TEXT,
    
    -- SEO and Visibility
    seo_title TEXT,
    seo_description TEXT,
    keywords TEXT, -- JSON array for search optimization
    
    -- Workflow and Approval
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by INTEGER,
    approved_at TEXT,
    rejection_reason TEXT,
    
    -- Scheduling
    start_date DATE,
    posted_at TEXT,
    expires_at TEXT,
    last_updated_at TEXT,
    
    -- Analytics
    views_count INTEGER DEFAULT 0,
    applications_present INTEGER DEFAULT 0,
    bookmarks_count INTEGER DEFAULT 0,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT,
    updated_at TEXT,
    
    -- Foreign Keys
    FOREIGN KEY (employer_id) REFERENCES employers(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES job_categories(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    CHECK (employment_type IN ('full-time', 'part-time', 'contract', 'freelance', 'internship')),
    CHECK (experience_level IN ('entry', 'junior', 'mid', 'senior', 'executive')),
    CHECK (education_level IN ('high_school', 'associate', 'bachelor', 'master', 'phd', 'none')),
    CHECK (status IN ('draft', 'active', 'paused', 'closed', 'expired')),
    CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    CHECK (remote_type IN ('fully_remote', 'hybrid', 'onsite')),
    CHECK (salary_type IN ('hourly', 'daily', 'weekly', 'monthly', 'annual')),
    CHECK (application_method IN ('internal', 'external', 'email')),
    CHECK (salary_min >= 0),
    CHECK (salary_max >= salary_min OR salary_max IS NULL),
    CHECK (max_applications > 0 OR max_applications IS NULL),
    CHECK (applications_count >= 0),
    CHECK (views_count >= 0),
    CHECK (bookmarks_count >= 0),
    CHECK (LENGTH(title) >= 3),
    CHECK (LENGTH(description) >= 10)
);

-- Job Skills Table (for structured skill requirements)
CREATE TABLE IF NOT EXISTS job_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    skill_category TEXT, -- 'technical', 'soft', 'language', 'certification', 'tool'
    is_required BOOLEAN DEFAULT TRUE,
    proficiency_level TEXT, -- 'beginner', 'intermediate', 'advanced', 'expert'
    years_experience INTEGER DEFAULT 0,
    created_at TEXT,
    
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    
    CHECK (skill_category IN ('technical', 'soft', 'language', 'certification', 'tool')),
    CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    CHECK (years_experience >= 0),
    
    UNIQUE(job_id, skill_name) -- Prevent duplicate skills per job
);

-- Job Questions Table (for application screening questions)
CREATE TABLE IF NOT EXISTS job_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT DEFAULT 'text', -- 'text', 'textarea', 'multiple_choice', 'yes_no', 'number', 'date'
    options TEXT, -- JSON array for multiple choice questions
    is_required BOOLEAN DEFAULT FALSE,
    order_index INTEGER DEFAULT 0,
    max_length INTEGER,
    created_at TEXT,
    
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    
    CHECK (question_type IN ('text', 'textarea', 'multiple_choice', 'yes_no', 'number', 'date')),
    CHECK (order_index >= 0),
    CHECK (max_length IS NULL OR max_length > 0)
);

-- Job Bookmarks Table (for candidates to save jobs)
CREATE TABLE IF NOT EXISTS job_bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    notes TEXT,
    created_at TEXT,
    
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    UNIQUE(job_id, user_id) -- Prevent duplicate bookmarks
);

-- Job Views Table (for analytics)
CREATE TABLE IF NOT EXISTS job_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    user_id INTEGER, -- NULL for anonymous views
    ip_address TEXT,
    user_agent TEXT,
    referrer TEXT,
    viewed_at TEXT,
    
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Job Templates Table (for employers to create job templates)
CREATE TABLE IF NOT EXISTS job_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER NOT NULL,
    template_name TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    requirements TEXT,
    responsibilities TEXT,
    benefits TEXT,
    employment_type TEXT NOT NULL,
    experience_level TEXT,
    education_level TEXT,
    required_skills TEXT, -- JSON array
    preferred_skills TEXT, -- JSON array
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    
    FOREIGN KEY (employer_id) REFERENCES employers(id) ON DELETE CASCADE,
    
    CHECK (employment_type IN ('full-time', 'part-time', 'contract', 'freelance', 'internship')),
    CHECK (experience_level IN ('entry', 'junior', 'mid', 'senior', 'executive')),
    CHECK (education_level IN ('high_school', 'associate', 'bachelor', 'master', 'phd', 'none')),
    CHECK (usage_count >= 0)
);

-- Job Alerts Table (for candidate job alerts)
CREATE TABLE IF NOT EXISTS job_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    alert_name TEXT NOT NULL,
    keywords TEXT, -- JSON array of keywords
    location TEXT,
    employment_type TEXT, -- JSON array
    experience_level TEXT, -- JSON array
    salary_min DECIMAL(10, 2),
    remote_type TEXT, -- JSON array
    email_frequency TEXT DEFAULT 'daily', -- 'immediate', 'daily', 'weekly'
    is_active BOOLEAN DEFAULT TRUE,
    last_sent_at TEXT,
    created_at TEXT,
    updated_at TEXT,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    CHECK (email_frequency IN ('immediate', 'daily', 'weekly'))
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_jobs_employer_id ON jobs(employer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_category_id ON jobs(category_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_employment_type ON jobs(employment_type);
CREATE INDEX IF NOT EXISTS idx_jobs_experience_level ON jobs(experience_level);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city);
CREATE INDEX IF NOT EXISTS idx_jobs_country ON jobs(country);
CREATE INDEX IF NOT EXISTS idx_jobs_is_remote ON jobs(is_remote);
CREATE INDEX IF NOT EXISTS idx_jobs_remote_type ON jobs(remote_type);
CREATE INDEX IF NOT EXISTS idx_jobs_is_featured ON jobs(is_featured);
CREATE INDEX IF NOT EXISTS idx_jobs_is_urgent ON jobs(is_urgent);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs(posted_at);
CREATE INDEX IF NOT EXISTS idx_jobs_expires_at ON jobs(expires_at);
CREATE INDEX IF NOT EXISTS idx_jobs_application_deadline ON jobs(application_deadline);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_salary_range ON jobs(salary_min, salary_max);

CREATE INDEX IF NOT EXISTS idx_job_categories_name ON job_categories(name);
CREATE INDEX IF NOT EXISTS idx_job_categories_is_active ON job_categories(is_active);

CREATE INDEX IF NOT EXISTS idx_job_skills_job_id ON job_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill_name ON job_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill_category ON job_skills(skill_category);
CREATE INDEX IF NOT EXISTS idx_job_skills_is_required ON job_skills(is_required);

CREATE INDEX IF NOT EXISTS idx_job_questions_job_id ON job_questions(job_id);
CREATE INDEX IF NOT EXISTS idx_job_questions_order_index ON job_questions(order_index);

CREATE INDEX IF NOT EXISTS idx_job_bookmarks_job_id ON job_bookmarks(job_id);
CREATE INDEX IF NOT EXISTS idx_job_bookmarks_user_id ON job_bookmarks(user_id);

CREATE INDEX IF NOT EXISTS idx_job_views_job_id ON job_views(job_id);
CREATE INDEX IF NOT EXISTS idx_job_views_user_id ON job_views(user_id);
CREATE INDEX IF NOT EXISTS idx_job_views_viewed_at ON job_views(viewed_at);

CREATE INDEX IF NOT EXISTS idx_job_templates_employer_id ON job_templates(employer_id);
CREATE INDEX IF NOT EXISTS idx_job_templates_is_active ON job_templates(is_active);

CREATE INDEX IF NOT EXISTS idx_job_alerts_user_id ON job_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_job_alerts_is_active ON job_alerts(is_active);

-- Insert default job categories
INSERT OR IGNORE INTO job_categories (name, description, is_active) VALUES
('Technology', 'Software development, IT, and tech-related positions', 1),
('Sales & Marketing', 'Sales, marketing, and business development roles', 1),
('Finance & Accounting', 'Financial, accounting, and banking positions', 1),
('Healthcare', 'Medical, nursing, and healthcare-related jobs', 1),
('Education', 'Teaching, training, and educational roles', 1),
('Engineering', 'Civil, mechanical, electrical, and other engineering positions', 1),
('Human Resources', 'HR, recruitment, and people management roles', 1),
('Customer Service', 'Customer support and service positions', 1),
('Operations', 'Operations, logistics, and supply chain roles', 1),
('Design & Creative', 'Graphic design, UX/UI, and creative positions', 1),
('Legal', 'Legal, compliance, and paralegal positions', 1),
('Manufacturing', 'Production, manufacturing, and industrial jobs', 1),
('Retail', 'Retail, merchandising, and store management', 1),
('Hospitality', 'Hotels, restaurants, and tourism industry', 1),
('Transportation', 'Logistics, delivery, and transportation roles', 1),
('Real Estate', 'Real estate, property management, and construction', 1),
('Non-Profit', 'NGO, charity, and social service positions', 1),
('Government', 'Public sector and government positions', 1),
('Media & Communications', 'Journalism, PR, and media-related roles', 1),
('Other', 'Miscellaneous and uncategorized positions', 1);

-- job applications table
-- This table tracks job applications made by users for specific jobs

CREATE TABLE IF NOT EXISTS job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    application_date TEXT,
    status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    notes TEXT,
    
    -- Resume PDF fields
    resume_filename TEXT,
    resume_path TEXT,
    resume_size INTEGER,
    resume_uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- saved jobs table
CREATE TABLE IF NOT EXISTS saved_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,

    UNIQUE(user_id, job_id)  
);


