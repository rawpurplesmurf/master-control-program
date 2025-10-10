-- Drop and recreate prompt templates table with MCP function calling support
-- 
-- Template Placeholder Syntax:
-- {variable} - Data fetcher variables
-- [system_prompt:name] - References a system prompt from system_prompts table
-- [skippy_guard_rail:name] - References a rule with name 'skippy_guard_rail_name' from rules table
--
DROP TABLE IF EXISTS prompt_templates;

CREATE TABLE prompt_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL UNIQUE,
    intent_keywords TEXT NOT NULL,
    user_template TEXT NOT NULL,
    system_prompt TEXT, -- DEPRECATED: System prompts now come from system_prompts table
    pre_fetch_data JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_prompt_templates_name (template_name),
    INDEX idx_prompt_templates_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert MCP-compatible templates with function calling support
INSERT INTO prompt_templates (template_name, intent_keywords, user_template, system_prompt, pre_fetch_data, is_active) VALUES

('device_control', 'turn on,turn off,switch,control,toggle,dim,brighten', 
'Command: {command}
Available devices: {controllable_entities}
[skippy_guard_rail:garden_light]

Use the control_device function to execute this command. Confirm the action after execution.', 
'[system_prompt:default_mcp]',
'["controllable_entities"]', TRUE),

('status_query', 'status,state,what is,how is,temperature,humidity,check', 
'Question: {command}
Current device states: {all_entities}

Answer this question directly based on the current state data. Do not use functions for simple queries.', 
'[system_prompt:simple_assistant]',
'["all_entities"]', TRUE),

('automation_creation', 'create rule,automate,when,if then,schedule,trigger', 
'Automation request: {command}
Available devices: {controllable_entities}
Current automations: {existing_rules}

Use the create_automation function to set up this automation based on the request.', 
'[system_prompt:automation_focused]',
'["controllable_entities", "existing_rules"]', TRUE),

('lighting_control', 'lights,lamp,brightness,color,scene', 
'Lighting command: {command}
Current lights: {lights_data}
[skippy_guard_rail:garden_light]

Use the control_device function for light control. Support brightness, color changes, and scenes.', 
'[system_prompt:default_mcp]',
'["lights_data"]', TRUE),

('climate_control', 'temperature,heat,cool,thermostat,climate,hvac', 
'Climate command: {command}
Climate devices: {climate_data}
Current weather: {weather_data}

Use control_device function for climate control. Consider current conditions.', 
'[system_prompt:default_mcp]',
'["climate_data", "weather_data"]', TRUE),

('security_monitoring', 'lock,unlock,security,door,window,alarm', 
'Security command: {command}
Security devices: {security_data}
Recent activity: {recent_events}

Use control_device function for security actions. Always confirm security changes.', 
'[system_prompt:default_mcp]',
'["security_data", "recent_events"]', TRUE),

('entertainment_control', 'music,play,volume,tv,media,sound', 
'Entertainment command: {command}
Media devices: {media_data}

Use control_device function to control entertainment systems and media players.', 
'[system_prompt:conversational]',
'["media_data"]', TRUE),

('general_assistant', 'help,what can,how do,explain,tell me', 
'Question: {command}
System capabilities: {system_info}

Answer this question directly. Explain available functions and capabilities without executing them.', 
'[system_prompt:technical_expert]',
'["system_info"]', TRUE),

('default', 'default,fallback', 
'Command: {command}
Context: {context_data}

Process this command appropriately. Use functions for actions, respond directly for questions.', 
'[system_prompt:default_mcp]',
'["context_data"]', TRUE);
