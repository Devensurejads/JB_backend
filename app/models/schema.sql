-- app/models/schema.sql
-- Job Management System Database Schema

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Users Table (for authentication and user management)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    role TEXT NOT NULL DEFAULT 'employee', -- 'superadmin', 'admin', 'staff', 'employee', 'employer'
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    -- created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT,
    updated_at TEXT,

    email_verification_token TEXT,
    email_verification_token_expires TEXT,
    
    -- Constraints
    CHECK (role IN ('superadmin', 'admin', 'staff', 'employee', 'employer')),
    CHECK (LENGTH(username) >= 3),
    CHECK (LENGTH(email) >= 5)
);

CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token);

-- User Profiles Table (extended user information)
CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    zip_code TEXT,
    date_of_birth DATE,
    gender TEXT,
    bio TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    portfolio_url TEXT,
    resume_url TEXT,
    profile_image_url TEXT,
    skills TEXT, -- JSON array of skills
    experience_years INTEGER DEFAULT 0,
    current_position TEXT,
    current_company TEXT,
    education TEXT, -- JSON array of education
    certifications TEXT, -- JSON array of certifications
    languages TEXT, -- JSON array of languages
    availability TEXT DEFAULT 'available', -- 'available', 'employed', 'not_looking'
    salary_expectation_min DECIMAL(10, 2),
    salary_expectation_max DECIMAL(10, 2),
    preferred_location TEXT,
    willing_to_relocate BOOLEAN DEFAULT FALSE,
    preferred_employment_type TEXT, -- JSON array of preferred types
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    CHECK (availability IN ('available', 'employed', 'not_looking')),
    CHECK (experience_years >= 0),
    CHECK (salary_expectation_min >= 0),
    CHECK (salary_expectation_max >= salary_expectation_min)
);

-- Audit Logs Table (for tracking all system changes)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, -- NULL for system actions
    action TEXT NOT NULL, -- 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', etc.
    entity_type TEXT NOT NULL, -- 'user', 'job', 'application', etc.
    entity_id INTEGER, -- ID of the affected entity
    changes TEXT, -- JSON object with old/new values
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- System Settings Table
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    description TEXT,
    category TEXT,
    is_public BOOLEAN DEFAULT FALSE, -- Whether setting is visible to non-admin users
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File Uploads Table
CREATE TABLE IF NOT EXISTS file_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'resume', 'cover_letter', 'profile_image', 'company_logo', etc.
    related_id INTEGER, -- Related entity ID (job_id, application_id, etc.)
    related_type TEXT, -- Related entity type
    is_public BOOLEAN DEFAULT FALSE,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    CHECK (file_size > 0)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Insert default data
INSERT OR IGNORE INTO system_settings (key, value, description, category, is_public) VALUES
('site_name', 'Job Management System', 'Website name', 'general', 1),
('site_description', 'A comprehensive job management platform', 'Website description', 'general', 1),
('admin_email', 'admin@jobmanagement.com', 'Administrator email', 'general', 0),
('max_file_size', '10485760', 'Maximum file upload size in bytes (10MB)', 'files', 0),
('allowed_file_types', '["pdf", "doc", "docx", "jpg", "jpeg", "png"]', 'Allowed file types for uploads', 'files', 0),
('jwt_expiry_hours', '24', 'JWT token expiry in hours', 'security', 0),
('password_min_length', '8', 'Minimum password length', 'security', 0),
('enable_email_notifications', 'true', 'Enable email notifications', 'notifications', 0),
('items_per_page', '20', 'Default items per page for listings', 'pagination', 0);

-- Create a default superadmin user (password: Admin123!)
-- Note: In production, this should be changed immediately
INSERT OR IGNORE INTO users (username, password_hash, email, first_name, last_name, role, is_active) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeStMIEUOuK8F8sTm', 'admin@jobmanagement.com', 'System', 'Administrator', 'superadmin', 1);


------------------------Footer Section Tables------------------------

-- Contact Us Table
CREATE TABLE IF NOT EXISTS contact_us (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Recommended Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_contact_us_email ON contact_us(email);
CREATE INDEX IF NOT EXISTS idx_contact_us_subject ON contact_us(subject);

CREATE TABLE IF NOT EXISTS terms_of_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index to improve performance on content searches if needed
-- Create the index for the title column if it doesn't already exist
CREATE INDEX IF NOT EXISTS idx_terms_of_service_title ON terms_of_service(title);

-- Insert the Terms of Service data into the database
INSERT INTO terms_of_service (title, content)
VALUES (
    'Terms of Service',
    'Introduction:\nBy accessing this website or using the services provided herein, you agree to be bound by the terms and conditions outlined below. Please read them carefully before using the service.\n\nDefinitions:\n- "Service" refers to the services provided by this website.\n- "User" refers to individuals who access or use the services.\n- "Company" refers to the company providing the service.\n\nEligibility:\nTo use our services, you must be at least 18 years of age or have the legal capacity to enter into contracts in your jurisdiction.\n\nAccount Registration:\nTo use the services, you must create an account. During the registration process, you will be required to provide personal details, including your name, email, phone number, and other relevant information.\n\nUser Obligations:\n- You agree to provide accurate, complete, and updated information when registering.\n- You must protect your account credentials and notify us immediately if you suspect any unauthorized use.\n\nJob Posting Guidelines (for Employers):\n- Employers must ensure that all job postings comply with local labor laws and are not discriminatory.\n- Employers should not post jobs that violate any applicable laws or regulations.\n\nApplication Process (for Job Seekers):\n- Job seekers must provide accurate and truthful information during the application process.\n- Job seekers agree to follow the company''s application procedures.\n\nFees and Payments:\n- The services are free for job seekers. Employers may be required to pay for premium job listings.\n- Payments must be made in full before the services are rendered.\n\nContent Ownership and License:\n- The company owns the content provided on the platform, including text, images, and other materials.\n- Users may not reproduce, modify, or distribute any content without permission.\n\nPrivacy Policy:\n- We value your privacy and will not share your personal data without your consent, except as required by law.\n- Please refer to our Privacy Policy for more details on how we collect, store, and use your data.\n\nGoverning Law and Dispute Resolution:\n- These terms are governed by the laws of the jurisdiction where the company is based.\n- Any disputes arising out of these terms will be resolved through binding arbitration.\n\nChanges to Terms:\n- The company may update these Terms of Service at any time. Any changes will be posted on this page, and the updated date will be reflected at the top.\n\nContact Information:\nFor questions about these Terms of Service, please contact us at:\nEmail: support@company.com\nPhone: +91 7039422922'
);


-- Privacy Policy Table
CREATE TABLE IF NOT EXISTS privacy_policy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_privacy_policy_title ON privacy_policy(title);
INSERT INTO privacy_policy (title, content)
VALUES (
    'Privacy Policy',
    'Introduction:\nAt [Company Name], we value your privacy and are committed to protecting your personal data. This privacy policy explains how we collect, use, store, and protect your information.\n\nInformation We Collect:\n- Personal identification information (Name, Email, Phone Number, etc.)\n- Non-personal identification information (Browser type, IP address, etc.)\n\nHow We Use Your Information:\n- To improve our website and services\n- To respond to your inquiries\n- To send promotional materials (if you opt-in)\n\nSharing Your Information:\nWe do not sell, trade, or rent your personal data to third parties. However, we may share your information with trusted partners who assist us in operating our website, conducting business, or serving you.\n\nData Security:\nWe take reasonable measures to protect your data, including encryption and secure storage practices.\n\nYour Data Protection Rights:\n- Access: You can request a copy of your personal data.\n- Correction: You can correct any inaccurate data.\n- Deletion: You can request the deletion of your data under certain circumstances.\n\nCookies:\nWe use cookies to enhance your experience on our website. You can control cookie preferences through your browser settings.\n\nChanges to This Policy:\nWe may update this privacy policy from time to time. Any changes will be posted on this page with an updated date.\n\nContact Information:\nFor any questions regarding this privacy policy, please contact us at:\nEmail: support@company.com\nPhone: +91 7039422922'
);

