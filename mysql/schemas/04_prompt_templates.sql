-- Schema for prompt_templates table
CREATE TABLE IF NOT EXISTS prompt_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_name VARCHAR(128) NOT NULL,
    intent_keywords TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    user_template TEXT NOT NULL,
    pre_fetch_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
