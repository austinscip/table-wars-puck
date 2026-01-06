"""
TRIVIA WARS - Flask Routes
API endpoints for YDKJ-style trivia games
"""

from flask import Blueprint, jsonify, request, render_template
from flask_socketio import emit
from trivia_database import (
    get_random_question, get_category_by_name,
    create_trivia_session, add_player_to_session,
    execute_query, get_placeholder
)
from trivia_game_engines import create_game_engine
from trivia_session_manager import TriviaSessionManager, pick_random_skill_game, get_51_skill_games

# Create Blueprint
trivia_bp = Blueprint('trivia', __name__)

# Store active game sessions in memory
active_sessions = {}


# ========================================
# WEB PAGES
# ========================================

@trivia_bp.route('/trivia')
def trivia_home():
    """Trivia mode selection page"""
    return render_template('trivia_home.html')


@trivia_bp.route('/trivia/tv/<session_code>')
def trivia_tv_display(session_code):
    """TV display for trivia game"""
    return render_template('trivia_tv.html', session_code=session_code)


@trivia_bp.route('/trivia/results/<session_code>')
def trivia_results_page(session_code):
    """Results page for completed trivia session"""
    # Get session details for context
    ph = get_placeholder()
    session = execute_query(
        f'''SELECT s.*, b.slug as bar_slug, b.name as bar_name
            FROM trivia_sessions s
            JOIN bars b ON s.bar_id = b.id
            WHERE s.session_code = {ph}''',
        (session_code,),
        fetch_one=True
    )

    if not session:
        return "Session not found", 404

    return render_template('trivia_results.html',
                          session_code=session_code,
                          bar_slug=session['bar_slug'],
                          table_number=session['table_number'])


# ========================================
# API - SESSION MANAGEMENT
# ========================================

@trivia_bp.route('/api/trivia/start', methods=['POST'])
def api_start_trivia():
    """
    Start a new trivia session

    POST /api/trivia/start
    {
        "bar_slug": "demo-bar",
        "table_number": 1,
        "game_type": "category_royale",
        "players": [
            {"puck_id": 1, "player_name": "Player 1"},
            {"puck_id": 2, "player_name": "Player 2"}
        ]
    }
    """
    data = request.get_json()

    bar_slug = data.get('bar_slug')
    table_number = data.get('table_number')
    game_type = data.get('game_type', 'category_royale')
    players = data.get('players', [])

    if not bar_slug or not players:
        return jsonify({'error': 'Missing required fields'}), 400

    # Get bar ID
    ph = get_placeholder()
    bar = execute_query(f'SELECT id FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return jsonify({'error': 'Bar not found'}), 404

    # Get game type ID
    game_type_row = execute_query(
        f'SELECT id FROM trivia_game_types WHERE name = {ph}',
        (game_type,),
        fetch_one=True
    )

    if not game_type_row:
        return jsonify({'error': 'Game type not found'}), 404

    # Create session
    session_code = create_trivia_session(bar['id'], table_number, game_type_row['id'])

    # Get session ID
    session = execute_query(
        f'SELECT id FROM trivia_sessions WHERE session_code = {ph}',
        (session_code,),
        fetch_one=True
    )

    # Add players
    for player in players:
        add_player_to_session(session['id'], player['puck_id'], player.get('player_name'))

    # Create game engine
    engine = create_game_engine(game_type, session['id'], players)
    active_sessions[session_code] = engine

    # Start game
    initial_state = engine.start_game()

    return jsonify({
        'success': True,
        'session_code': session_code,
        'session_id': session['id'],
        'game_state': initial_state,
        'tv_url': f'/trivia/tv/{session_code}'
    })


@trivia_bp.route('/api/trivia/session/<session_code>', methods=['GET'])
def api_get_session(session_code):
    """
    Get current session state
    Returns phase: 'trivia_round', 'skill_break', or 'final_results'
    """
    try:
        manager = TriviaSessionManager(session_code)
        state = manager.get_session_state()

        return jsonify({
            'success': True,
            **state
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


# ========================================
# API - GAME FLOW
# ========================================

@trivia_bp.route('/api/trivia/question/<session_code>', methods=['GET'])
def api_load_question(session_code):
    """
    Load next question in curated session
    Automatically picks difficulty based on round position
    """
    try:
        manager = TriviaSessionManager(session_code)
        state = manager.get_session_state()

        if state['phase'] != 'trivia_round':
            return jsonify({
                'error': f"Cannot load question during {state['phase']}",
                'phase': state['phase']
            }), 400

        question = manager.get_next_question()

        if not question:
            return jsonify({'error': 'No questions available'}), 404

        # Get category info
        ph = get_placeholder()
        category = execute_query(
            f'SELECT * FROM trivia_categories WHERE id = {ph}',
            (question['category_id'],),
            fetch_one=True
        )

        return jsonify({
            'success': True,
            'question': {
                'id': question['id'],
                'setup': question['setup_text'],
                'question': question['question_text'],
                'answers': {
                    'A': question['answer_a'],
                    'B': question['answer_b'],
                    'C': question['answer_c'],
                    'D': question['answer_d']
                },
                'difficulty': question['difficulty'],
                'time_limit': question['time_limit'],
                'category': category['name'],
                'category_emoji': category['emoji']
            },
            'round': state['round'],
            'question_number': (state['questions_completed'] % 5) + 1
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@trivia_bp.route('/api/trivia/answer', methods=['POST'])
def api_submit_answer():
    """
    Submit answer in curated session

    POST /api/trivia/answer
    {
        "session_code": "ABC123",
        "puck_id": 1,
        "question_id": 5,
        "answer": "A",
        "response_time_ms": 3500
    }
    """
    data = request.get_json()

    session_code = data.get('session_code')
    puck_id = data.get('puck_id')
    question_id = data.get('question_id')
    answer = data.get('answer')
    response_time_ms = data.get('response_time_ms', 0)

    try:
        # Get question
        ph = get_placeholder()
        question = execute_query(
            f'SELECT * FROM trivia_questions WHERE id = {ph}',
            (question_id,),
            fetch_one=True
        )

        if not question:
            return jsonify({'error': 'Question not found'}), 404

        # Check if correct
        is_correct = (answer == question['correct_answer'])

        # Calculate points (basic: 1000 for correct, 0 for wrong)
        # Could be enhanced with time-based scoring
        points = 1000 if is_correct else 0

        # Get session ID
        session = execute_query(
            f'SELECT id FROM trivia_sessions WHERE session_code = {ph}',
            (session_code,),
            fetch_one=True
        )

        # Record answer
        from trivia_database import record_answer
        record_answer(
            session['id'],
            question_id,
            puck_id,
            answer,
            is_correct,
            response_time_ms,
            points
        )

        # Check if round complete
        manager = TriviaSessionManager(session_code)
        status = manager.complete_question()

        # Get commentary
        commentary = question['host_commentary_correct'] if is_correct else question['host_commentary_wrong']

        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'points': points,
            'explanation': question['explanation'],
            'commentary': commentary,
            'correct_answer': question['correct_answer'],
            'next_phase': status['status']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@trivia_bp.route('/api/trivia/results/<session_code>', methods=['GET'])
def api_get_results(session_code):
    """Get final session results"""
    try:
        manager = TriviaSessionManager(session_code)
        results = manager.get_final_results()

        return jsonify({
            'success': True,
            **results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@trivia_bp.route('/api/trivia/skill-break/start', methods=['POST'])
def api_start_skill_break():
    """
    Start skill break between trivia rounds

    POST /api/trivia/skill-break/start
    {
        "session_code": "ABC123",
        "skill_game_id": 5,  // Optional - will pick random if not provided
        "skill_game_name": "Shake Master"
    }
    """
    data = request.get_json()
    session_code = data.get('session_code')

    try:
        manager = TriviaSessionManager(session_code)
        state = manager.get_session_state()

        if state['phase'] != 'skill_break':
            return jsonify({
                'error': 'Not in skill break phase',
                'current_phase': state['phase']
            }), 400

        # Pick random skill game if not specified
        if 'skill_game_id' in data:
            skill_game = {
                'id': data['skill_game_id'],
                'name': data['skill_game_name']
            }
        else:
            skill_game = pick_random_skill_game()

        manager.start_skill_break(skill_game['id'], skill_game['name'])

        return jsonify({
            'success': True,
            'skill_game': skill_game,
            'message': f"Get ready to play {skill_game['name']}!"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@trivia_bp.route('/api/trivia/skill-break/complete', methods=['POST'])
def api_complete_skill_break():
    """
    Complete skill break and record winner

    POST /api/trivia/skill-break/complete
    {
        "session_code": "ABC123",
        "winner_puck_id": 1,
        "bonus_points": 500
    }
    """
    data = request.get_json()
    session_code = data.get('session_code')
    winner_puck_id = data.get('winner_puck_id')
    bonus_points = data.get('bonus_points', 500)

    try:
        manager = TriviaSessionManager(session_code)
        manager.complete_skill_break(winner_puck_id, bonus_points)

        return jsonify({
            'success': True,
            'message': f'Skill break complete! +{bonus_points} bonus points awarded',
            'next_phase': 'trivia_round'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@trivia_bp.route('/api/trivia/skill-games', methods=['GET'])
def api_get_skill_games():
    """Get list of 51 skill games available for breaks"""
    games = get_51_skill_games()
    return jsonify({
        'success': True,
        'games': games,
        'total': len(games)
    })


@trivia_bp.route('/api/trivia/next-round/<session_code>', methods=['POST'])
def api_next_round(session_code):
    """Move to next round"""
    engine = active_sessions.get(session_code)

    if not engine:
        return jsonify({'error': 'Session not found'}), 404

    engine.next_round()

    return jsonify({
        'success': True,
        'round': engine.round_number
    })


# ========================================
# API - GAME-SPECIFIC MECHANICS
# ========================================

@trivia_bp.route('/api/trivia/screw', methods=['POST'])
def api_activate_screw():
    """
    Activate screw mechanic (Screw Your Neighbor game)

    POST /api/trivia/screw
    {
        "session_code": "ABC123",
        "screwer_puck_id": 1,
        "target_puck_id": 2
    }
    """
    data = request.get_json()

    session_code = data.get('session_code')
    screwer_puck_id = data.get('screwer_puck_id')
    target_puck_id = data.get('target_puck_id')

    engine = active_sessions.get(session_code)

    if not engine:
        return jsonify({'error': 'Session not found'}), 404

    if not hasattr(engine, 'activate_screw'):
        return jsonify({'error': 'Screw mechanic not available in this game type'}), 400

    result = engine.activate_screw(screwer_puck_id, target_puck_id)

    return jsonify({
        'success': True,
        **result
    })


@trivia_bp.route('/api/trivia/multiplier', methods=['POST'])
def api_set_multiplier():
    """
    Set multiplier (Multiplier Madness game)

    POST /api/trivia/multiplier
    {
        "session_code": "ABC123",
        "puck_id": 1,
        "spin_speed": 250
    }
    """
    data = request.get_json()

    session_code = data.get('session_code')
    puck_id = data.get('puck_id')
    spin_speed = data.get('spin_speed')

    engine = active_sessions.get(session_code)

    if not engine:
        return jsonify({'error': 'Session not found'}), 404

    if not hasattr(engine, 'set_multiplier'):
        return jsonify({'error': 'Multiplier mechanic not available in this game type'}), 400

    result = engine.set_multiplier(puck_id, spin_speed)

    return jsonify({
        'success': True,
        **result
    })


# ========================================
# API - CATEGORIES & QUESTIONS
# ========================================

@trivia_bp.route('/api/trivia/categories', methods=['GET'])
def api_get_categories():
    """Get all active categories"""
    ph = get_placeholder()

    categories = execute_query(
        f'SELECT * FROM trivia_categories WHERE is_active = {ph} ORDER BY name',
        (True,),
        fetch_all=True
    )

    return jsonify({
        'success': True,
        'categories': categories
    })


@trivia_bp.route('/api/trivia/game-types', methods=['GET'])
def api_get_game_types():
    """Get all available game types"""
    ph = get_placeholder()

    game_types = execute_query(
        f'SELECT * FROM trivia_game_types WHERE is_active = {ph} ORDER BY name',
        (True,),
        fetch_all=True
    )

    return jsonify({
        'success': True,
        'game_types': game_types
    })


# ========================================
# API - ADMIN
# ========================================

@trivia_bp.route('/api/trivia/admin/questions', methods=['GET', 'POST'])
def api_admin_questions():
    """
    GET: List all questions
    POST: Add new question
    """
    if request.method == 'GET':
        ph = get_placeholder()
        questions = execute_query(
            f'''SELECT q.*, c.name as category_name
                FROM trivia_questions q
                JOIN trivia_categories c ON q.category_id = c.id
                ORDER BY q.created_at DESC
                LIMIT 100''',
            fetch_all=True
        )

        return jsonify({
            'success': True,
            'questions': questions
        })

    elif request.method == 'POST':
        # Add new question
        data = request.get_json()

        # Required fields
        required = ['category_id', 'question_text', 'answer_a', 'answer_b', 'answer_c', 'answer_d', 'correct_answer']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400

        ph = get_placeholder()

        try:
            execute_query(f'''
                INSERT INTO trivia_questions
                (category_id, question_text, setup_text, answer_a, answer_b, answer_c, answer_d,
                 correct_answer, difficulty, time_limit, explanation,
                 host_commentary_correct, host_commentary_wrong)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ''', (
                data['category_id'],
                data['question_text'],
                data.get('setup_text', ''),
                data['answer_a'],
                data['answer_b'],
                data['answer_c'],
                data['answer_d'],
                data['correct_answer'],
                data.get('difficulty', 'medium'),
                data.get('time_limit', 15),
                data.get('explanation', ''),
                data.get('host_commentary_correct', ''),
                data.get('host_commentary_wrong', '')
            ))

            return jsonify({
                'success': True,
                'message': 'Question added successfully'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500


# ========================================
# WEBSOCKET EVENTS (to be integrated with socketio)
# ========================================

def register_trivia_socketio_events(socketio):
    """Register WebSocket events for real-time trivia"""

    @socketio.on('trivia_join_session')
    def handle_join_session(data):
        session_code = data.get('session_code')
        emit('trivia_joined', {'session_code': session_code})

    @socketio.on('trivia_puck_shake')
    def handle_puck_shake(data):
        """Handle puck shake events (for category selection, etc.)"""
        session_code = data.get('session_code')
        puck_id = data.get('puck_id')
        intensity = data.get('intensity')

        emit('trivia_shake_registered', {
            'puck_id': puck_id,
            'intensity': intensity
        }, room=session_code)

    @socketio.on('trivia_answer_submitted')
    def handle_answer_broadcast(data):
        """Broadcast when answer is submitted"""
        session_code = data.get('session_code')
        emit('trivia_answer_received', data, room=session_code)


# Export blueprint
def init_trivia_routes(app, socketio=None):
    """Initialize trivia routes"""
    app.register_blueprint(trivia_bp)

    if socketio:
        register_trivia_socketio_events(socketio)

    print("✅ Trivia routes initialized")
