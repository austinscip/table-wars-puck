# Server Agent Instructions

## Overview

This directory contains the Flask backend for Table Wars. The server handles:
- WebSocket real-time communication
- Game state management
- Leaderboards and scoring
- Firmware OTA management
- Database persistence

## Architecture

```
app.py                  # Main Flask application (port 5001)
database.py             # SQLite/Postgres abstraction
templates/              # Jinja2 HTML templates
static/                 # CSS, JS, images

Route Modules:
├── trivia_routes.py    # Trivia game endpoints
├── tv_game_routes.py   # Screen-centric game endpoints
├── multiplayer_routes.py # Multi-puck game endpoints
├── firmware_routes.py  # OTA firmware management
└── trivia_database.py  # Trivia question storage
```

## Flask + WebSocket Pattern

```python
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# HTTP Route
@app.route('/game/<game_name>')
def game_page(game_name):
    return render_template(f'games/{game_name}.html')

# WebSocket Event Handler
@socketio.on('player_action')
def handle_player_action(data):
    # Process action
    game_state = process_action(data)
    # Broadcast to all clients
    emit('game_update', game_state, broadcast=True)

# WebSocket Namespace (for game isolation)
@socketio.on('spin', namespace='/game/shot-roulette')
def handle_spin(data):
    velocity = data['velocity']
    # Process spin...
    emit('wheel_spin', {'velocity': velocity}, namespace='/game/shot-roulette', broadcast=True)
```

## Database Pattern

```python
from database import execute_query, get_placeholder

# Query with placeholder (works with SQLite and Postgres)
ph = get_placeholder()
results = execute_query(
    f'SELECT * FROM games WHERE puck_id = {ph}',
    (puck_id,),
    fetch_all=True
)

# Insert
execute_query(
    f'INSERT INTO scores (puck_id, score) VALUES ({ph}, {ph})',
    (puck_id, score)
)
```

## Game State Management

```python
# In-memory game state (for real-time games)
active_games = {}

def create_game(game_id, game_type):
    active_games[game_id] = {
        'type': game_type,
        'players': [],
        'state': 'waiting',
        'round': 0,
        'created_at': datetime.now()
    }

def add_player(game_id, puck_id, name):
    if game_id in active_games:
        active_games[game_id]['players'].append({
            'puck_id': puck_id,
            'name': name,
            'score': 0,
            'status': 'active'
        })
        # Broadcast player joined
        socketio.emit('player_joined', {
            'puck_id': puck_id,
            'name': name
        }, room=game_id)
```

## WebSocket Events Pattern

```python
# Client → Server events (receive)
@socketio.on('connect')
@socketio.on('disconnect')
@socketio.on('join_game')
@socketio.on('player_action')
@socketio.on('spin')
@socketio.on('tap')
@socketio.on('shake_data')

# Server → Client events (emit)
emit('game_update', data, broadcast=True)
emit('player_joined', data, room=game_id)
emit('round_start', data, namespace='/game/shot-roulette')
emit('wheel_result', data, to=player_sid)
```

## Template Pattern

```html
<!-- templates/games/shot-roulette.html -->
{% extends "base.html" %}

{% block content %}
<div id="game-container">
    <canvas id="wheel-canvas"></canvas>
    <div id="player-list"></div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
<script>
    const socket = io('/game/shot-roulette');

    socket.on('connect', () => {
        console.log('Connected to game server');
    });

    socket.on('wheel_spin', (data) => {
        spinWheel(data.velocity);
    });
</script>
{% endblock %}
```

## API Endpoints Pattern

```python
# REST endpoints for puck communication
@app.route('/api/puck/register', methods=['POST'])
def register_puck():
    data = request.json
    puck_id = data['puck_id']
    # Register puck...
    return jsonify({'status': 'ok'})

@app.route('/api/game/<game_id>/join', methods=['POST'])
def join_game(game_id):
    data = request.json
    puck_id = data['puck_id']
    # Add player to game...
    return jsonify({'status': 'joined', 'game_id': game_id})

@app.route('/api/score', methods=['POST'])
def submit_score():
    data = request.json
    save_score(data['puck_id'], data['game_type'], data['score'])
    return jsonify({'status': 'saved'})
```

## Running the Server

```bash
# Development
python app.py

# With auto-reload
FLASK_ENV=development python app.py

# Production (use gunicorn)
gunicorn -k eventlet -w 1 app:app -b 0.0.0.0:5001
```

## Key Gotchas

1. **WebSocket CORS**: Always set `cors_allowed_origins="*"` for development
2. **Namespace isolation**: Use namespaces to isolate game types
3. **Room management**: Use `join_room()` / `leave_room()` for game sessions
4. **State persistence**: In-memory state is lost on restart - use database for important data
5. **Broadcast vs emit**: `broadcast=True` sends to all, `room=X` sends to room members

## Important URLs

- Dashboard: http://localhost:5001/
- Leaderboard: http://localhost:5001/leaderboard
- Firmware OTA: http://localhost:5001/firmware/dashboard
- Game pages: http://localhost:5001/game/<game-name>
