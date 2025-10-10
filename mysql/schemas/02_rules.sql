-- Enhanced Rules table schema supporting both Skippy Guardrails and Submind Rules
DROP TABLE IF EXISTS rules;
CREATE TABLE rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    rule_type ENUM('skippy_guardrail', 'submind_automation') NOT NULL,
    
    -- Common fields
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,  -- Using INTEGER for boolean compatibility
    priority INTEGER NOT NULL DEFAULT 0,  -- Higher numbers = higher priority
    
    -- Skippy Guardrail fields
    target_entity_pattern VARCHAR(255),  -- e.g., "light.garden_*", "climate.*"
    blocked_actions JSON,                -- ["turn_on", "set_brightness"] 
    guard_conditions JSON,               -- {"time_range": "06:00-20:00", "sensor_states": {...}}
    override_keywords TEXT,              -- Comma-separated keywords to bypass guardrail
    
    -- Submind Automation fields  
    trigger_conditions JSON,             -- {"presence": true, "time": "after_sunset"}
    target_actions JSON,                 -- [{"entity": "light.living_room", "action": "turn_on"}]
    execution_schedule VARCHAR(100),     -- "immediate", "delayed_5min", "cron:0 */15 * * *"
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_executed TIMESTAMP NULL,
    execution_count INTEGER NOT NULL DEFAULT 0,
    
    -- Indexes for performance
    INDEX idx_rule_type (rule_type),
    INDEX idx_active_priority (is_active, priority),
    INDEX idx_target_pattern (target_entity_pattern)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sample rules data
-- Note: The rule_name should follow the pattern 'skippy_guard_rail_name'
-- In templates, reference these using [skippy_guard_rail:name] (without the prefix)
INSERT INTO rules (
    rule_name, 
    rule_type, 
    description, 
    is_active, 
    priority, 
    target_entity_pattern, 
    blocked_actions, 
    guard_conditions, 
    override_keywords,
    trigger_conditions,
    target_actions
) VALUES (
    'skippy_guard_rail_garden_light',
    'skippy_guardrail',
    'Prevent garden lights during extended daylight hours',
    1,
    0,
    'light.garden_*',
    '["turn_on"]',
    '{"time_after": "05:30", "time_before": "19:00"}',
    'emergency, force',
    '{}',
    '[]'
);

INSERT INTO rules (
    rule_name, 
    rule_type, 
    description, 
    is_active, 
    priority, 
    trigger_conditions, 
    target_actions,
    execution_schedule
) VALUES (
    'Submind Automation - Arrival lights',
    'submind_automation',
    'Turn on entrance lights when arriving after sunset',
    1,
    10,
    '{"entity_id": "binary_sensor.front_door", "state": "on", "sun_position": "below_horizon"}',
    '[{"service": "light.turn_on", "entity_id": "light.entryway"}, {"service": "light.turn_on", "entity_id": "light.porch"}]',
    'immediate'
);
