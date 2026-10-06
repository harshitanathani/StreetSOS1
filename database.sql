CREATE DATABASE IF NOT EXISTS streetsos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE streetsos;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS complaint_status_history;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('citizen','worker','admin') NOT NULL DEFAULT 'citizen',
    department ENUM('Road','Garbage','Drainage','Lighting','General') NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_department (department)
);

CREATE TABLE complaints (
    complaint_id INT AUTO_INCREMENT PRIMARY KEY,
    public_id VARCHAR(32) NOT NULL UNIQUE,
    citizen_id INT NOT NULL,
    category ENUM('Road','Garbage','Drainage','Lighting') NOT NULL,
    issue_type VARCHAR(60) NOT NULL,
    location_type ENUM('Highway','Main Road','Residential Area','Market / Public Area','Other') NOT NULL,
    description TEXT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    area VARCHAR(120) NOT NULL,
    street VARCHAR(160) NULL,
    landmark VARCHAR(160) NULL,
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    severity_score TINYINT NOT NULL,
    severity_label ENUM('Low','Medium','High','Critical') NOT NULL,
    status ENUM('Reported','Assigned','In Progress','Resolved','Verified') NOT NULL DEFAULT 'Reported',
    assigned_worker_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_at DATETIME NULL,
    started_at DATETIME NULL,
    sla_deadline DATETIME NOT NULL,
    is_escalated BOOLEAN NOT NULL DEFAULT FALSE,
    escalated_at DATETIME NULL,
    resolved_at DATETIME NULL,
    resolution_note TEXT NULL,
    resolution_image_path VARCHAR(255) NULL,
    verified_at DATETIME NULL,
    CONSTRAINT fk_complaint_citizen FOREIGN KEY (citizen_id) REFERENCES users(user_id),
    CONSTRAINT fk_complaint_worker FOREIGN KEY (assigned_worker_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_complaint_status (status),
    INDEX idx_complaint_category (category),
    INDEX idx_complaint_severity (severity_score),
    INDEX idx_complaint_sla (sla_deadline, is_escalated),
    INDEX idx_complaint_worker (assigned_worker_id),
    INDEX idx_complaint_citizen (citizen_id)
);

CREATE TABLE complaint_status_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    from_status VARCHAR(30) NULL,
    to_status VARCHAR(30) NOT NULL,
    changed_by INT NULL,
    note VARCHAR(500) NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_history_complaint FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    CONSTRAINT fk_history_user FOREIGN KEY (changed_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_history_complaint (complaint_id, changed_at)
);
