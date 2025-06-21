# Claude Computer Use Demo - FastAPI Backend

(refer testing.md for testing CURL commands, and google drive for the demo video link https://drive.google.com/file/d/1irq6TaF0mAhDUhsUqV299D8tw2f3ygd9/view?usp=sharing )

This is a FastAPI-based backend that replaces the experimental Streamlit interface with a modern, scalable API that provides:

- **Session Management**: Create, manage, and persist chat sessions
- **Real-time Communication**: WebSocket-based real-time updates
- **VNC Integration**: Virtual machine access via VNC/noVNC
- **Database Persistence**: SQLite-based chat history storage
- **Docker Support**: Easy deployment and development

## Features

### 🚀 FastAPI Backend
- **RESTful APIs** for session management and chat
- **WebSocket support** for real-time communication
- **Async/await** architecture for high performance
- **Automatic API documentation** (Swagger UI at `/docs`)

### 💾 Database Persistence
- **SQLite database** for session and message storage
- **Automatic cleanup** of old sessions
- **Message history** with tool execution results

### 🔌 Real-time Communication
- **WebSocket connections** per session
- **Live progress updates** during processing
- **Tool execution notifications**
- **Error handling** with real-time feedback

### 🖥️ VNC Integration
- **VNC server** management
- **noVNC web interface** for browser access
- **Automatic startup/shutdown**
- **Connection status monitoring**

## Quick Start

### Prerequisites
- Docker and Docker Compose
- API key from Anthropic, AWS Bedrock, or Google Vertex

### 1. Clone and Build
```bash
git clone <repository-url>
cd computer-use-demo
docker-compose build
```

### 2. Start the Services
```bash
# Start the FastAPI backend
docker-compose up -d computer-use-fastapi

# Or start with nginx (production)
docker-compose --profile production up -d
```

### 3. Access the Application
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **VNC Interface**: http://localhost:8080 (after starting VNC)

## API Endpoints

### Session Management
- `POST /api/sessions` - Create a new session
- `GET /api/sessions/{session_id}` - Get session details
- `DELETE /api/sessions/{session_id}` - Delete a session
- `GET /api/sessions/{session_id}/messages` - Get session messages

### Chat Interface
- `POST /api/sessions/{session_id}/chat` - Send a message
- `WebSocket /ws/{session_id}` - Real-time updates

### VNC Management
- `GET /api/vnc/status` - Get VNC status
- `POST /api/vnc/connect` - Start VNC server

## Usage Examples

### Create a Session
```bash
curl -X POST "http://localhost:8000/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "your-api-key",
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022-v2:0",
    "system_prompt": "You are a helpful assistant."
  }'
```

### Send a Message
```bash
curl -X POST "http://localhost:8000/api/sessions/{session_id}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, can you help me with a task?"
  }'
```

### WebSocket Connection
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  switch(data.type) {
    case 'assistant_message':
      console.log('Assistant:', data.content);
      break;
    case 'tool_use':
      console.log('Tool used:', data.tool_name);
      break;
    case 'tool_result':
      console.log('Tool result:', data.output);
      break;
  }
};
```

## Frontend Interface

The application includes a modern HTML/JavaScript frontend with:

- **Session Management UI** - Create and manage sessions
- **Real-time Chat Interface** - Live message updates
- **VNC Integration** - Embedded VNC viewer
- **Status Indicators** - Connection and processing status
- **Responsive Design** - Works on desktop and mobile

## Development

### Local Development Setup
```bash
# Install Python dependencies
pip install -r fastapi_app/requirements.txt
pip install -r computer_use_demo/requirements.txt

# Run the FastAPI server
cd fastapi_app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Project Structure
```
fastapi_app/
├── main.py              # FastAPI application entry point
├── models.py            # Pydantic models for API schemas
├── database.py          # Database manager for SQLite
├── session_manager.py   # Session management logic
├── computer_loop.py     # Integration with computer use tools
├── vnc_manager.py       # VNC server management
└── requirements.txt     # Python dependencies

static/
└── index.html          # Frontend interface

computer_use_demo/      # Original computer use tools
├── loop.py
├── tools/
└── requirements.txt
```

### Environment Variables
- `ANTHROPIC_API_KEY` - Anthropic API key
- `AWS_ACCESS_KEY_ID` - AWS credentials for Bedrock
- `AWS_SECRET_ACCESS_KEY` - AWS credentials for Bedrock
- `GOOGLE_APPLICATION_CREDENTIALS` - Google credentials for Vertex

## Docker Deployment

### Production Deployment
```bash
# Build and run with nginx
docker-compose --profile production up -d

# Scale the application
docker-compose up -d --scale computer-use-fastapi=3
```

### Custom Configuration
```bash
# Use custom ports
docker run -p 9000:8000 -p 5902:5901 computer-use-fastapi

# Mount custom volumes
docker run -v /path/to/data:/home/computeruse/data computer-use-fastapi
```

## Monitoring and Logs

### View Logs
```bash
# Application logs
docker-compose logs -f computer-use-fastapi

# Database logs
docker exec -it computer-use-fastapi tail -f /home/computeruse/logs/app.log
```

### Health Checks
- **API Health**: `GET /health`
- **Database Status**: Check SQLite database file
- **VNC Status**: `GET /api/vnc/status`

## Troubleshooting

### Common Issues

1. **VNC Connection Failed**
   - Check if Xvfb is running: `docker exec -it container ps aux | grep Xvfb`
   - Verify VNC port is exposed: `docker port container 5901`

2. **WebSocket Connection Issues**
   - Ensure WebSocket proxy is configured in nginx
   - Check firewall settings for WebSocket ports

3. **Database Errors**
   - Verify SQLite file permissions
   - Check database file path in volume mounts

4. **API Key Issues**
   - Verify API key is valid
   - Check provider configuration
   - Ensure proper environment variables are set

### Performance Optimization

1. **Database Optimization**
   - Enable WAL mode for SQLite
   - Regular cleanup of old sessions
   - Index optimization for message queries

2. **Memory Management**
   - Monitor WebSocket connections
   - Implement connection pooling
   - Regular garbage collection

3. **Scaling**
   - Use Redis for session storage
   - Implement load balancing
   - Database sharding for high traffic

## Security Considerations

- **API Key Security**: Store API keys securely, never in code
- **VNC Security**: Use VNC passwords in production
- **WebSocket Security**: Implement authentication for WebSocket connections
- **Database Security**: Use encrypted SQLite or PostgreSQL in production
- **Network Security**: Use HTTPS in production with proper SSL certificates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the same license as the original computer-use-demo project. 