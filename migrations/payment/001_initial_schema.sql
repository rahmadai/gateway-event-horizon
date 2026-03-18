-- Initial schema for Payment Service

CREATE DATABASE IF NOT EXISTS payment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE payment;

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    stripe_customer_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_stripe_id (stripe_customer_id),
    INDEX idx_email (email)
) ENGINE=InnoDB;

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    payment_intent_id VARCHAR(255) UNIQUE,
    customer_id BIGINT UNSIGNED,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status ENUM('pending', 'succeeded', 'failed', 'refunded', 'partially_refunded') DEFAULT 'pending',
    payment_method VARCHAR(100),
    idempotency_key VARCHAR(255) UNIQUE,
    description TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_payment_intent (payment_intent_id),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_idempotency (idempotency_key),
    INDEX idx_created (created_at),
    
    CONSTRAINT fk_payments_customer 
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Refunds table
CREATE TABLE IF NOT EXISTS refunds (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    refund_id VARCHAR(255) UNIQUE,
    payment_id BIGINT UNSIGNED NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    reason VARCHAR(255),
    status ENUM('pending', 'succeeded', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_refund_id (refund_id),
    INDEX idx_payment (payment_id),
    
    CONSTRAINT fk_refunds_payment 
        FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Webhook events table (for audit and replay)
CREATE TABLE IF NOT EXISTS webhook_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    payload JSON NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_event_id (event_id),
    INDEX idx_event_type (event_type),
    INDEX idx_processed (processed)
) ENGINE=InnoDB;

-- Insert sample data
INSERT INTO customers (id, stripe_customer_id, email, name) VALUES
(1, 'cus_sample1', 'customer1@example.com', 'Customer One'),
(2, 'cus_sample2', 'customer2@example.com', 'Customer Two')
ON DUPLICATE KEY UPDATE id=id;

INSERT INTO payments (id, payment_intent_id, customer_id, amount, currency, status, description) VALUES
(1, 'pi_sample1', 1, 100.00, 'USD', 'succeeded', 'Sample payment 1'),
(2, 'pi_sample2', 2, 250.50, 'USD', 'succeeded', 'Sample payment 2')
ON DUPLICATE KEY UPDATE id=id;
