"""
Flask Routes for Multiplayer Games (70-73)
"""

from flask import Blueprint, render_template, request, jsonify
from flask_socketio import emit, join_room
from multiplayer_engines import (
    start_multiplayer_game,
    update_multiplayer_game,
    end_multiplayer_game,
    get_multiplayer_game_state
)

multiplayer_bp = Blueprint('multiplayer', __name__)

# ============================================================================
# REST API ROUTES
# ============================================================================

@multiplayer_bp.route('/multiplayer/start/<int:game_id>', methods=['POST'])
def start_mp_game(game_id):
    """
    Start a new multiplayer game
    POST /multiplayer/start/70
    Body: {"player_ids": [1, 2, 3, 4], "team_assignments": {1: 1, 2: 1, 3: 2, 4: 2}}
    """
    data = request.get_json()
    player_ids = data.get('player_ids', [])
    team_assignments = data.get('team_assignments')

    if not player_ids:
        return jsonify({"error": "player_ids required"}), 400

    if game_id not in [70, 71, 72, 73]:
        return jsonify({"error": "Invalid game_id"}), 400

    try:
        session_id, initial_state = start_multiplayer_game(game_id, player_ids, team_assignments)
        return jsonify({
            "success": True,
            "session_id": session_id,
            "game_id": game_id,
            "state": initial_state
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@multiplayer_bp.route('/multiplayer/state/<int:session_id>', methods=['GET'])
def get_mp_game_state(session_id):
    """Get current game state for a session"""
    state = get_multiplayer_game_state(session_id)

    if state is None:
        return jsonify({"error": "No active game for this session"}), 404

    return jsonify(state)


@multiplayer_bp.route('/multiplayer/end/<int:session_id>', methods=['POST'])
def end_mp_game(session_id):
    """End a multiplayer game"""
    success = end_multiplayer_game(session_id)

    if not success:
        return jsonify({"error": "No active game for this session"}), 404

    return jsonify({"success": True})


# ============================================================================
# TV DISPLAY ROUTES
# ============================================================================

@multiplayer_bp.route('/tv/keep-away-chaos')
def tv_keep_away():
    """TV display for Keep Away Chaos (Game 70)"""
    return render_template('tv_games/keep_away_chaos.html')


@multiplayer_bp.route('/tv/tug-of-war')
def tv_tug_of_war():
    """TV display for Tug of War (Game 71)"""
    return render_template('tv_games/tug_of_war.html')


@multiplayer_bp.route('/tv/bomb-lobber')
def tv_bomb_lobber():
    """TV display for Bomb Lobber (Game 72)"""
    return render_template('tv_games/bomb_lobber.html')


@multiplayer_bp.route('/tv/simon-says')
def tv_simon_says():
    """TV display for Simon Says Survival (Game 73)"""
    return render_template('tv_games/simon_says.html')


# ============================================================================
# GAME LOBBY
# ============================================================================

@multiplayer_bp.route('/lobby')
def game_lobby():
    """Multiplayer game lobby - select game and players"""
    return render_template('multiplayer_lobby.html')


# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

def register_multiplayer_socketio(socketio):
    """Register WebSocket handlers for multiplayer games"""

    @socketio.on('multiplayer_input')
    def handle_multiplayer_input(data):
        """
        Receive puck input and update multiplayer game state

        Expected data:
        {
            "session_id": 1234567890,
            "puck_id": 1,
            "tilt_x": -15.3,
            "tilt_y": 8.2,
            "shake_intensity": 12.5,
            "button_held": false
        }
        """
        session_id = data.get('session_id')
        puck_id = data.get('puck_id')

        if not session_id or not puck_id:
            emit('error', {"message": "session_id and puck_id required"})
            return

        # Update game state
        new_state = update_multiplayer_game(session_id, puck_id, data)

        if new_state:
            # Broadcast updated state to all players
            emit('multiplayer_state_update', new_state, broadcast=True, room=f'session_{session_id}')

            # Check if game is over
            if new_state.get('game_over'):
                emit('multiplayer_game_over', {
                    "session_id": session_id,
                    "state": new_state
                }, broadcast=True, room=f'session_{session_id}')


    @socketio.on('join_multiplayer_session')
    def handle_join_session(data):
        """Player/TV joins multiplayer session room"""
        session_id = data.get('session_id')
        if session_id:
            join_room(f'session_{session_id}')
            emit('joined', {"message": f"Joined session {session_id}"})

            # Send current state
            state = get_multiplayer_game_state(session_id)
            if state:
                emit('multiplayer_state_update', state)


def init_multiplayer_routes(app, socketio):
    """Initialize multiplayer routes and WebSocket handlers"""
    app.register_blueprint(multiplayer_bp)
    register_multiplayer_socketio(socketio)
    print("✅ Multiplayer routes and WebSocket handlers registered")
