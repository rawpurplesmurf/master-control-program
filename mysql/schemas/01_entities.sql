CREATE TABLE IF NOT EXISTS entities (
    entity_id VARCHAR(255) PRIMARY KEY,
    friendly_name VARCHAR(255) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    last_updated DATETIME NOT NULL
);

