
# Project To-Do List

Based on the project's design documents and current implementation, here are the features and improvements that still need to be implemented:

**Core Functionality:**

*   **Conditional Logic (`check_state`):** The ability to handle commands with conditions (e.g., "If the living room is dark, turn on the light") is not yet implemented. The `action_executor.py` file has a placeholder comment indicating that this logic is missing.
~~*   **Redis Caching:** The design document specifies that Redis should be used to cache command responses to avoid unnecessary calls to Ollama. This caching logic has not been implemented in the `router.py` file.~~
*   **Action History Endpoint:** The `GET /api/history/{entity_id}` endpoint, which is supposed to provide a history of actions for a specific device, has not been created.
*   ~~**Prompt History Endpoint:** An endpoint for the UI to read the `prompt_history` from the database or cache is also missing.~~ this is done, went with redis only for now.
* ~~**Ollama Integration:** we need to inplement calling ollama correctly with chunking switched off.~~ done

**User Interface:**

*   ~~**UI for Rule Management:** The "Future Work" section mentions a user interface for managing the rules in the database. The `skippy` directory, intended for the frontend, is currently empty.~~
we built an API for this. 

**Advanced Features:**

*   ~~**Home Assistant WebSocket Integration:** The project currently polls Home Assistant for updates every 30 minutes. The plan is to switch to a WebSocket integration for real-time updates.~~
*   **`submind` Module:** The purpose of the `submind` module is not clearly defined, and the directory is empty. This component still needs to be designed and implemented.
