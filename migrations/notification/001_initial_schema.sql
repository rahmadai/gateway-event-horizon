-- Initial schema for Notification Service

CREATE DATABASE IF NOT EXISTS notification CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE notification;

-- Email templates table
CREATE TABLE IF NOT EXISTS email_templates (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    subject_template TEXT NOT NULL,
    body_text_template TEXT,
    body_html_template TEXT,
    variables JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Email logs table
CREATE TABLE IF NOT EXISTS email_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    status ENUM('queued', 'sent', 'delivered', 'failed', 'bounced') DEFAULT 'queued',
    template_id VARCHAR(100),
    error_message TEXT,
    sent_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_message_id (message_id),
    INDEX idx_recipient (recipient),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- Notification preferences
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id BIGINT UNSIGNED PRIMARY KEY,
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    push_enabled BOOLEAN DEFAULT TRUE,
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Insert default templates
INSERT INTO email_templates (id, name, subject_template, body_text_template, variables) VALUES
('welcome', 'Welcome Email', 'Welcome to {{service_name}}!', 'Hi {{name}}, welcome!', '["name", "service_name"]'),
('password_reset', 'Password Reset', 'Reset your password', 'Click here to reset', '["name", "reset_url"]')
ON DUPLICATE KEY UPDATE id=id;
