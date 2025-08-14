-- Add to app/models/schema.sql
-- Employee Management Tables

-- Employees Table - extends user functionality for employee-specific data

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    
    -- Personal Information
    date_of_birth DATE,
    gender TEXT, -- 'male', 'female', 'other', 'prefer_not_to_say'
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    zip_code TEXT,
    
    -- Professional Information
    current_position TEXT,
    current_company TEXT,
    experience_years INTEGER DEFAULT 0,
    resume_url TEXT,
    portfolio_url TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    profile_url TEXT,
    qualification TEXT,
    office_address TEXT,
    
    -- Job Preferences
    preferred_job_type TEXT, -- 'full-time', 'part-time', 'contract', 'freelance', 'internship'
    preferred_location TEXT,
    willing_to_relocate BOOLEAN DEFAULT FALSE,
    preferred_salary_min DECIMAL(10, 2),
    preferred_salary_max DECIMAL(10, 2),
    preferred_currency TEXT DEFAULT 'USD',
    remote_work_preference TEXT DEFAULT 'hybrid', -- 'onsite', 'remote', 'hybrid', 'no_preference'
    
    -- Availability
    availability_status TEXT DEFAULT 'available', -- 'available', 'employed', 'not_looking', 'interview_only'
    available_from DATE,
    notice_period_days INTEGER DEFAULT 0,
    
    -- Profile Information
    summary TEXT,
    skills TEXT, -- JSON array of skills
    languages TEXT, -- JSON array of languages with proficiency
    certifications TEXT, -- JSON array of certifications
    education TEXT, -- JSON array of education details
    work_experience TEXT, -- JSON array of work experience
    
    -- Privacy Settings
    profile_visibility TEXT DEFAULT 'public', -- 'public', 'private', 'employers_only'
    show_contact_info BOOLEAN DEFAULT TRUE,
    allow_recruiter_contact BOOLEAN DEFAULT TRUE,
    
    -- System Fields
    profile_completion DECIMAL(5, 2) DEFAULT 0.00,
    last_profile_update TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_date TIMESTAMP,
    verified_by INTEGER,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT, -- Internal admin notes
    created_at TEXT,
    updated_at TEXT,
    
    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    CHECK (preferred_job_type IN ('full-time', 'part-time', 'contract', 'freelance', 'internship')),
    CHECK (remote_work_preference IN ('onsite', 'remote', 'hybrid', 'no_preference')),
    CHECK (availability_status IN ('available', 'employed', 'not_looking', 'interview_only')),
    CHECK (profile_visibility IN ('public', 'private', 'employers_only')),
    CHECK (experience_years >= 0),
    CHECK (notice_period_days >= 0),
    CHECK (preferred_salary_min >= 0),
    CHECK (preferred_salary_max >= preferred_salary_min OR preferred_salary_max IS NULL),
    CHECK (profile_completion >= 0 AND profile_completion <= 100)
);

-- Employee Skills Table (for structured skill management)
CREATE TABLE IF NOT EXISTS employee_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    skill_category TEXT, -- 'technical', 'soft', 'language', 'certification', 'tool'
    proficiency_level TEXT, -- 'beginner', 'intermediate', 'advanced', 'expert'
    years_experience INTEGER DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE, -- Mark as primary/core skill
    created_at TEXT,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    
    CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    CHECK (skill_category IN ('technical', 'soft', 'language', 'certification', 'tool')),
    CHECK (years_experience >= 0),
    
    UNIQUE(employee_id, skill_name) -- Prevent duplicate skills per employee
);

-- Employee Education Table
CREATE TABLE IF NOT EXISTS employee_education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    institution_name TEXT NOT NULL,
    degree_type TEXT, -- 'high_school', 'associate', 'bachelor', 'master', 'phd', 'certificate', 'diploma'
    degree_title TEXT,
    field_of_study TEXT,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    gpa DECIMAL(3, 2),
    max_gpa DECIMAL(3, 2) DEFAULT 4.00,
    description TEXT,
    created_at TEXT,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    
    CHECK (degree_type IN ('high_school', 'associate', 'bachelor', 'master', 'phd', 'certificate', 'diploma')),
    CHECK (gpa IS NULL OR (gpa >= 0 AND gpa <= max_gpa)),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Employee Work Experience Table
CREATE TABLE IF NOT EXISTS employee_work_experience (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    position_title TEXT NOT NULL,
    employment_type TEXT, -- 'full-time', 'part-time', 'contract', 'freelance', 'internship'
    start_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    location TEXT,
    description TEXT,
    achievements TEXT,
    skills_used TEXT, -- JSON array of skills
    created_at TEXT,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    
    CHECK (employment_type IN ('full-time', 'part-time', 'contract', 'freelance', 'internship')),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Employee Certifications Table
CREATE TABLE IF NOT EXISTS employee_certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    certification_name TEXT NOT NULL,
    issuing_organization TEXT NOT NULL,
    credential_id TEXT,
    issue_date DATE,
    expiry_date DATE,
    never_expires BOOLEAN DEFAULT FALSE,
    verification_url TEXT,
    description TEXT,
    created_at TEXT,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    
    CHECK (expiry_date IS NULL OR never_expires = TRUE OR expiry_date >= issue_date)
);

-- Employee Documents Table (for storing resumes, portfolios, etc.)
CREATE TABLE IF NOT EXISTS employee_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    document_type TEXT NOT NULL, -- 'resume', 'cover_letter', 'portfolio', 'certificate', 'transcript', 'other'
    file_name TEXT NOT NULL,
    original_file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE, -- Mark as primary document for type
    is_public BOOLEAN DEFAULT FALSE, -- Whether document is publicly viewable
    uploaded_at TEXT,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    
    CHECK (document_type IN ('resume', 'cover_letter', 'portfolio', 'certificate', 'transcript', 'other')),
    CHECK (file_size > 0)
);

-- Employee Job Preferences Table (for detailed job preferences)
CREATE TABLE IF NOT EXISTS employee_job_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL UNIQUE,
    preferred_industries TEXT, -- JSON array of preferred industries
    preferred_company_sizes TEXT, -- JSON array: 'startup', 'small', 'medium', 'large', 'enterprise'
    preferred_roles TEXT, -- JSON array of preferred job roles
    work_authorization TEXT, -- 'citizen', 'permanent_resident', 'work_visa', 'student_visa', 'no_authorization'
    requires_sponsorship BOOLEAN DEFAULT FALSE,
    preferred_benefits TEXT, -- JSON array of preferred benefits
    commute_distance_max INTEGER, -- Maximum commute distance in miles/km
    travel_willingness TEXT DEFAULT 'none', -- 'none', 'occasional', 'frequent', 'extensive'
    created_at TEXT,
    updated_at TEXT,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    
    CHECK (work_authorization IN ('citizen', 'permanent_resident', 'work_visa', 'student_visa', 'no_authorization')),
    CHECK (travel_willingness IN ('none', 'occasional', 'frequent', 'extensive')),
    CHECK (commute_distance_max IS NULL OR commute_distance_max >= 0)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_employees_user_id ON employees(user_id);
CREATE INDEX IF NOT EXISTS idx_employees_availability_status ON employees(availability_status);
CREATE INDEX IF NOT EXISTS idx_employees_preferred_job_type ON employees(preferred_job_type);
CREATE INDEX IF NOT EXISTS idx_employees_city ON employees(city);
CREATE INDEX IF NOT EXISTS idx_employees_country ON employees(country);
CREATE INDEX IF NOT EXISTS idx_employees_experience_years ON employees(experience_years);
CREATE INDEX IF NOT EXISTS idx_employees_is_verified ON employees(is_verified);
CREATE INDEX IF NOT EXISTS idx_employees_is_active ON employees(is_active);
CREATE INDEX IF NOT EXISTS idx_employees_profile_visibility ON employees(profile_visibility);
CREATE INDEX IF NOT EXISTS idx_employees_created_at ON employees(created_at);

CREATE INDEX IF NOT EXISTS idx_employee_skills_employee_id ON employee_skills(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_skills_skill_name ON employee_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_employee_skills_skill_category ON employee_skills(skill_category);
CREATE INDEX IF NOT EXISTS idx_employee_skills_proficiency_level ON employee_skills(proficiency_level);

CREATE INDEX IF NOT EXISTS idx_employee_education_employee_id ON employee_education(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_education_degree_type ON employee_education(degree_type);
CREATE INDEX IF NOT EXISTS idx_employee_education_institution ON employee_education(institution_name);

CREATE INDEX IF NOT EXISTS idx_employee_work_experience_employee_id ON employee_work_experience(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_work_experience_company ON employee_work_experience(company_name);
CREATE INDEX IF NOT EXISTS idx_employee_work_experience_position ON employee_work_experience(position_title);

CREATE INDEX IF NOT EXISTS idx_employee_certifications_employee_id ON employee_certifications(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_certifications_name ON employee_certifications(certification_name);

CREATE INDEX IF NOT EXISTS idx_employee_documents_employee_id ON employee_documents(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_documents_type ON employee_documents(document_type);

CREATE INDEX IF NOT EXISTS idx_employee_job_preferences_employee_id ON employee_job_preferences(employee_id);