"""
Flask Routes for TV-Integrated Games (52-56)
WebSocket-based real-time game control
"""

from flask import Blueprint, render_template, request, jsonify
from flask_socketio import emit
from datetime import datetime
import time
from tv_game_engines import (
    start_game,
    update_game,
    end_game,
    get_game_state,
    active_games
)

tv_games_bp = Blueprint('tv_games', __name__)

# Sprint 0.5: Packet statistics for connection health monitoring
packet_stats = {
    'total_packets': 0,
    'dropped_packets': 0,
    'last_update_time': None
}

# ============================================================================
# REST API ROUTES
# ============================================================================

@tv_games_bp.route('/tv-games/start/<int:game_id>', methods=['POST'])
def start_tv_game(game_id):
    """
    Start a new TV game
    POST /tv-games/start/52
    Body: {"puck_id": 1}
    """
    data = request.get_json()
    puck_id = data.get('puck_id')

    if not puck_id:
        return jsonify({"error": "puck_id required"}), 400

    if game_id not in [52, 53, 54, 55, 56, 57, 58, 59, 60, 61]:
        return jsonify({"error": "Invalid game_id"}), 400

    try:
        initial_state = start_game(puck_id, game_id)
        return jsonify({
            "success": True,
            "puck_id": puck_id,
            "game_id": game_id,
            "state": initial_state
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tv_games_bp.route('/tv-games/state/<int:puck_id>', methods=['GET'])
def get_tv_game_state(puck_id):
    """Get current game state for a puck"""
    state = get_game_state(puck_id)

    if state is None:
        return jsonify({"error": "No active game for this puck"}), 404

    return jsonify(state)


@tv_games_bp.route('/tv-games/end/<int:puck_id>', methods=['POST'])
def end_tv_game(puck_id):
    """End a TV game and return final score"""
    final_score = end_game(puck_id)

    if final_score is None:
        return jsonify({"error": "No active game for this puck"}), 404

    return jsonify({
        "success": True,
        "puck_id": puck_id,
        "final_score": final_score
    })


@tv_games_bp.route('/tv-games/active', methods=['GET'])
def get_active_games():
    """Get list of all active TV games"""
    games_list = []
    for puck_id, game in active_games.items():
        state = game.get_state()
        games_list.append({
            "puck_id": puck_id,
            "game_id": state.get("game_id"),
            "game_type": state.get("game_type"),
            "game_over": state.get("game_over", False)
        })

    return jsonify({"active_games": games_list})


@tv_games_bp.route('/api/health', methods=['GET'])
def api_health():
    """
    Sprint 0.5: Connection health statistics
    Returns packet counts and drop rate
    """
    total = packet_stats['total_packets']
    dropped = packet_stats['dropped_packets']

    # Calculate drop rate (avoid divide by zero)
    drop_rate = (dropped / total * 100) if total > 0 else 0

    return jsonify({
        'total_packets': total,
        'dropped_packets': dropped,
        'drop_rate': round(drop_rate, 2),
        'last_update_time': packet_stats['last_update_time']
    })


# ============================================================================
# TV DISPLAY ROUTES
# ============================================================================

@tv_games_bp.route('/tv/puck-racer/<int:puck_id>')
def tv_puck_racer(puck_id):
    """TV display for Puck Racer (Game 52)"""
    return render_template('tv_games/puck_racer.html', puck_id=puck_id)


@tv_games_bp.route('/tv/puck-racer-3d/<int:puck_id>')
def tv_puck_racer_3d(puck_id):
    """TV display for Puck Racer 3D (Game 52) - CINEMATIC VERSION"""
    return render_template('tv_games/puck_racer_3d.html', puck_id=puck_id)


@tv_games_bp.route('/tv/test-3d')
def tv_test_3d():
    """Simple 3D test - debugging"""
    return render_template('tv_games/test_3d_simple.html')


@tv_games_bp.route('/tv/obstacle-dodger/<int:puck_id>')
def tv_obstacle_dodger(puck_id):
    """TV display for Obstacle Dodger (Game 53)"""
    return render_template('tv_games/obstacle_dodger.html', puck_id=puck_id)


@tv_games_bp.route('/tv/puck-golf/<int:puck_id>')
def tv_puck_golf(puck_id):
    """TV display for Puck Golf (Game 54)"""
    return render_template('tv_games/puck_golf.html', puck_id=puck_id)


@tv_games_bp.route('/tv/space-invaders/<int:puck_id>')
def tv_space_invaders(puck_id):
    """TV display for Space Invaders (Game 55)"""
    return render_template('tv_games/space_invaders.html', puck_id=puck_id)


@tv_games_bp.route('/tv/pong-puck/<int:puck_id>')
def tv_pong_puck(puck_id):
    """TV display for Pong Puck (Game 56)"""
    return render_template('tv_games/pong_puck.html', puck_id=puck_id)


@tv_games_bp.route('/tv/claw-machine/<int:puck_id>')
def tv_claw_machine(puck_id):
    """TV display for Claw Machine (Game 57)"""
    return render_template('tv_games/claw_machine.html', puck_id=puck_id)


@tv_games_bp.route('/tv/stack-boxes/<int:puck_id>')
def tv_stack_boxes(puck_id):
    """TV display for Stack the Boxes (Game 58)"""
    return render_template('tv_games/stack_boxes.html', puck_id=puck_id)


@tv_games_bp.route('/tv/duck-hunt/<int:puck_id>')
def tv_duck_hunt(puck_id):
    """TV display for Duck Hunt (Game 59)"""
    return render_template('tv_games/duck_hunt.html', puck_id=puck_id)


@tv_games_bp.route('/tv/correlation-word/<int:puck_id>')
def tv_correlation_word(puck_id):
    """TV display for Correlation Word Game (Game 60)"""
    return render_template('tv_games/correlation_word.html', puck_id=puck_id)


@tv_games_bp.route('/tv/greyhound-racing/<int:puck_id>')
def tv_greyhound_racing(puck_id):
    """TV display for Greyhound Racing (Game 61)"""
    return render_template('tv_games/greyhound_racing.html', puck_id=puck_id)


@tv_games_bp.route('/tv/shot-roulette-royale/<int:puck_id>')
def tv_shot_roulette_royale(puck_id):
    """TV display for Shot Roulette Royale (Game 62)"""
    return render_template('tv_games/shot_roulette_royale.html', puck_id=puck_id)


# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

def register_tv_game_socketio(socketio):
    """Register WebSocket handlers for TV games"""

    @socketio.on('puck_input')
    def handle_puck_input(data):
        """
        Receive puck input and update game state

        Expected data:
        {
            "puck_id": 1,
            "tilt_x": -15.3,
            "tilt_y": 8.2,
            "gyro_z": 0.523,           # Raw gyro Z (rad/s)
            "spin_speed": 30.0,        # Spin speed (deg/s)
            "shake_intensity": 12.5,
            "shake_detected": true,
            "button_held": false,
            "timestamp": 1234567890
        }
        """
        puck_id = data.get('puck_id')
        tilt_x = data.get('tilt_x', 0)
        tilt_y = data.get('tilt_y', 0)
        gyro_z = data.get('gyro_z', 0)
        spin_speed = data.get('spin_speed', 0)
        shake_intensity = data.get('shake_intensity', 0)
        shake_detected = data.get('shake_detected', False)

        # Sprint 0.5: Update packet statistics
        packet_stats['total_packets'] += 1
        packet_stats['last_update_time'] = time.time()

        # Sprint 0D: Always broadcast sensor data for debug panel (separate event)
        print(f"📥 puck_input: puck={puck_id} spin={spin_speed:.1f} shake={shake_intensity:.1f}")
        emit('sensor_data_update', {
            'puck_id': puck_id,
            'tilt_x': tilt_x,
            'tilt_y': tilt_y,
            'gyro_z': gyro_z,
            'spin_speed': spin_speed,
            'shake_intensity': shake_intensity,
            'shake_detected': shake_detected,
            'timestamp': time.time()  # Sprint 0.5: Connection health monitoring
        }, broadcast=True)

        # If no active game, we're done (sensor data already broadcast)
        if not puck_id or puck_id not in active_games:
            return

        # Update game state
        new_state = update_game(puck_id, data)

        if new_state:
            # Broadcast updated state to TV displays
            emit('game_state_update', new_state, broadcast=True, room=f'game_{puck_id}')

            # Check if game is over
            if new_state.get('game_over'):
                final_score = end_game(puck_id)
                emit('game_over', {
                    "puck_id": puck_id,
                    "final_score": final_score,
                    "state": new_state
                }, broadcast=True, room=f'game_{puck_id}')


    @socketio.on('join_game_room')
    def handle_join_game_room(data):
        """TV display joins room to receive game updates"""
        puck_id = data.get('puck_id')
        if puck_id:
            from flask_socketio import join_room
            join_room(f'game_{puck_id}')
            emit('joined', {"message": f"Joined game room for puck {puck_id}"})


    @socketio.on('request_game_state')
    def handle_request_game_state(data):
        """Request current game state (for reconnection)"""
        puck_id = data.get('puck_id')
        if puck_id:
            state = get_game_state(puck_id)
            if state:
                emit('game_state_update', state)
            else:
                emit('error', {"message": "No active game"})


    @socketio.on('disconnect')
    def handle_disconnect():
        """
        Sprint 0.5: Track disconnections as dropped packets
        This helps identify connection instability in bar environments
        """
        packet_stats['dropped_packets'] += 1
        print(f"⚠️  Client disconnected - dropped packets: {packet_stats['dropped_packets']}")


def init_tv_game_routes(app, socketio):
    """Initialize TV game routes and WebSocket handlers"""
    app.register_blueprint(tv_games_bp)
    register_tv_game_socketio(socketio)
    print("✅ TV game routes and WebSocket handlers registered")
