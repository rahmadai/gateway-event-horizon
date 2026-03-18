-- Initial schema for Job Matching Service

CREATE DATABASE IF NOT EXISTS job_matching CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE job_matching;

-- Companies table (must be created first for foreign keys)
CREATE TABLE IF NOT EXISTS companies (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    size ENUM('startup', 'small', 'medium', 'enterprise'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Insert sample companies
INSERT INTO companies (id, name, industry, size) VALUES 
(1, 'TechCorp', 'Technology', 'enterprise'),
(2, 'StartupXYZ', 'Technology', 'startup'),
(3, 'Global Services', 'Services', 'medium')
ON DUPLICATE KEY UPDATE id=id;

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    company_id BIGINT UNSIGNED NOT NULL,
    location VARCHAR(100) NOT NULL,
    required_skills JSON NOT NULL,
    match_score DECIMAL(5,2) DEFAULT 0.00,
    status ENUM('active', 'paused', 'closed', 'filled') DEFAULT 'active',
    remote BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL DEFAULT NULL,
    
    INDEX idx_company (company_id),
    INDEX idx_status (status),
    INDEX idx_location_status_created (location, status, created_at),
    INDEX idx_status_score (status, match_score DESC),
    
    CONSTRAINT fk_jobs_company 
        FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- Candidates table
CREATE TABLE IF NOT EXISTS candidates (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    skills JSON NOT NULL,
    location VARCHAR(100) NOT NULL,
    experience_years TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_location (location),
    INDEX idx_experience (experience_years)
) ENGINE=InnoDB;

-- Job applications table
CREATE TABLE IF NOT EXISTS job_applications (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    candidate_id BIGINT UNSIGNED NOT NULL,
    status ENUM('pending', 'reviewed', 'interview', 'offer', 'hired', 'rejected') DEFAULT 'pending',
    cover_letter TEXT,
    resume_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL,
    decided_at TIMESTAMP NULL,
    
    UNIQUE KEY uniq_application (job_id, candidate_id),
    INDEX idx_candidate (candidate_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    INDEX idx_job_status (job_id, status),
    
    CONSTRAINT fk_app_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_app_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Insert sample data
INSERT INTO jobs (id, title, company_id, location, required_skills, match_score, status) VALUES
(1, 'Senior Python Engineer', 1, 'Jakarta', '["python", "fastapi", "mysql"]', 95.50, 'active'),
(2, 'Full Stack Developer', 2, 'Singapore', '["javascript", "python", "react"]', 88.00, 'active'),
(3, 'DevOps Engineer', 1, 'Remote', '["docker", "kubernetes", "aws"]', 92.00, 'active'),
(4, 'Data Engineer', 3, 'Jakarta', '["python", "sql", "spark"]', 85.00, 'active'),
(5, 'Backend Developer', 2, 'Bangkok', '["go", "postgresql", "redis"]', 78.00, 'active')
ON DUPLICATE KEY UPDATE id=id;

INSERT INTO candidates (id, name, email, skills, location, experience_years) VALUES
(1, 'John Doe', 'john@example.com', '["python", "fastapi", "docker"]', 'Jakarta', 5),
(2, 'Jane Smith', 'jane@example.com', '["javascript", "react", "node"]', 'Singapore', 3),
(3, 'Bob Wilson', 'bob@example.com', '["python", "sql", "spark"]', 'Jakarta', 7)
ON DUPLICATE KEY UPDATE id=id;

INSERT INTO job_applications (job_id, candidate_id, status) VALUES
(1, 1, 'pending'),
(1, 2, 'reviewed'),
(2, 2, 'pending'),
(3, 1, 'hired'),
(4, 3, 'interview')
ON DUPLICATE KEY UPDATE id=id;
