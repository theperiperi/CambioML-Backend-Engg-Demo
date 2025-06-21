

## API Documentation

### Session Endpoints

- **Create a new session**
  - `POST /api/sessions`
  - Example:
    ```bash
    curl -X POST http://localhost:8000/api/sessions \
      -H "Content-Type: application/json" \
      -d '{
        "api_key": "YOUR_API_KEY",
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "system_prompt": "You are a helpful assistant."
      }'
    ```

- **Get session details**
  - `GET /api/sessions/{session_id}`
  - Example:
    ```bash
    curl http://localhost:8000/api/sessions/SESSION_ID
    ```

- **Get all messages for a session**
  - `GET /api/sessions/{session_id}/messages`
  - Example:
    ```bash
    curl http://localhost:8000/api/sessions/SESSION_ID/messages
    ```

- **Send a chat message to a session**
  - `POST /api/sessions/{session_id}/chat`
  - Example:
    ```bash
    curl -X POST http://localhost:8000/api/sessions/SESSION_ID/chat \
      -H "Content-Type: application/json" \
      -d '{
        "message": "Hello, computer!"
      }'
    ```

- **Delete a session**
  - `DELETE /api/sessions/{session_id}`
  - Example:
    ```bash
    curl -X DELETE http://localhost:8000/api/sessions/SESSION_ID
    ```

### VNC Endpoints

- **Get VNC status**
  - `GET /api/vnc/status`
  - Example:
    ```bash
    curl http://localhost:8000/api/vnc/status
    ```

- **Start/connect to VNC**
  - `POST /api/vnc/connect`
  - Example:
    ```bash
    curl -X POST http://localhost:8000/api/vnc/connect
    ```

### WebSocket Endpoint

- **Real-time updates for a session**
  - `ws://localhost:8000/ws/{session_id}`
  - Connect using a WebSocket client to receive real-time assistant and tool messages.

---

For more details, see the FastAPI interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs) when the server is running.
