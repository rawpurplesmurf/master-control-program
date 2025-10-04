-- Data fetchers table for configurable pre-fetch data mappings
DROP TABLE IF EXISTS data_fetchers;
CREATE TABLE data_fetchers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fetcher_key VARCHAR(64) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    ttl_seconds INT DEFAULT 300,
    python_code TEXT NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fetcher_key (fetcher_key),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;