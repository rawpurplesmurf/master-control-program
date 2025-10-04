CREATE TABLE IF NOT EXISTS prompt_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    timestamp DATETIME NOT NULL,
    user_command TEXT NOT NULL,
    ollama_response TEXT NOT NULL,
    executed_actions TEXT NOT NULL,
    status VARCHAR(50) NOT NULL
);

