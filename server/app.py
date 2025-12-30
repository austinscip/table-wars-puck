"""
TABLE WARS - Web Scoreboard Server
Flask + WebSocket server for real-time leaderboard

Run with: python app.py
Access at: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime
import json

# Import database abstraction layer
from database import (
    init_database,
    get_db_connection,
    execute_query,
    get_placeholder,
    dict_from_row,
    USE_POSTGRES
)

# Import trivia routes and database
from trivia_routes import init_trivia_routes
from trivia_database import init_trivia_database, seed_trivia_data
from trivia_questions_seed import seed_questions

# Import TV game routes
from tv_game_routes import init_tv_game_routes

# Import multiplayer game routes
from multiplayer_routes import init_multiplayer_routes

# Import firmware OTA routes
from firmware_routes import init_firmware_routes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tablewars_secret_2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def register_puck(puck_id, name, table_number=1, battery_level=100):
    """Register or update a puck"""
    ph = get_placeholder()

    if USE_POSTGRES:
        query = f'''INSERT INTO pucks (id, name, table_number, battery_level, last_seen, is_online)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    table_number = EXCLUDED.table_number,
                    battery_level = EXCLUDED.battery_level,
                    last_seen = EXCLUDED.last_seen,
                    is_online = EXCLUDED.is_online'''
    else:
        query = f'''INSERT OR REPLACE INTO pucks
                    (id, name, table_number, battery_level, last_seen, is_online)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})'''

    execute_query(query, (puck_id, name, table_number, battery_level, datetime.now(), 1))

def save_score(puck_id, game_type, score, session_id=None):
    """Save a game score"""
    ph = get_placeholder()

    # Ensure puck exists
    puck = execute_query(f'SELECT id FROM pucks WHERE id = {ph}', (puck_id,), fetch_one=True)
    if not puck:
        register_puck(puck_id, f"Puck_{puck_id}")

    # Save score
    execute_query(f'''INSERT INTO games (bar_id, puck_id, game_id, game_type, score, session_id)
                      VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})''',
                  (None, puck_id, None, game_type, score, session_id))

    # Update puck stats
    execute_query(f'''UPDATE pucks SET
                      total_games_played = total_games_played + 1,
                      last_seen = {ph}
                      WHERE id = {ph}''',
                  (datetime.now(), puck_id))

    # Broadcast update via WebSocket
    socketio.emit('score_update', {
        'puck_id': puck_id,
        'game_type': game_type,
        'score': score,
        'timestamp': datetime.now().isoformat()
    })

def get_leaderboard(limit=10):
    """Get top players"""
    ph = get_placeholder()
    return execute_query(f'SELECT * FROM leaderboard LIMIT {ph}', (limit,), fetch_all=True)

def get_recent_games(limit=20):
    """Get recent game scores"""
    ph = get_placeholder()
    return execute_query(f'''SELECT g.*, p.name as puck_name
                             FROM games g
                             JOIN pucks p ON g.puck_id = p.id
                             ORDER BY g.timestamp DESC
                             LIMIT {ph}''', (limit,), fetch_all=True)

# ============================================================================
# HTTP ROUTES
# ============================================================================

@app.route('/')
def index():
    """System home page with navigation"""
    stats = {
        'total_games': execute_query('SELECT COUNT(*) as count FROM games', fetch_one=True)['count'],
        'total_pucks': execute_query('SELECT COUNT(*) as count FROM pucks', fetch_one=True)['count'],
        'total_score': execute_query('SELECT COALESCE(SUM(score), 0) as total FROM games', fetch_one=True)['total']
    }
    return render_template('index.html', stats=stats)

@app.route('/leaderboard')
def leaderboard():
    """Main leaderboard page"""
    return render_template('leaderboard.html')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for managing bars, games, and analytics"""
    return render_template('admin_dashboard.html')

@app.route('/api/leaderboard')
def api_leaderboard():
    """Get leaderboard JSON"""
    limit = request.args.get('limit', 10, type=int)
    return jsonify(get_leaderboard(limit))

@app.route('/api/recent')
def api_recent():
    """Get recent games JSON"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify(get_recent_games(limit))

@app.route('/api/puck/<int:puck_id>')
def api_puck(puck_id):
    """Get specific puck stats"""
    ph = get_placeholder()
    row = execute_query(f'SELECT * FROM leaderboard WHERE id = {ph}', (puck_id,), fetch_one=True)

    if row:
        return jsonify(row)
    else:
        return jsonify({'error': 'Puck not found'}), 404

@app.route('/api/score', methods=['POST'])
def api_submit_score():
    """
    Submit a score from a puck

    POST /api/score
    {
        "puck_id": 1,
        "game_type": "Speed Tap",
        "score": 470,
        "session_id": "optional_session_id"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    puck_id = data.get('puck_id')
    game_type = data.get('game_type')
    score = data.get('score')
    session_id = data.get('session_id')

    if not all([puck_id, game_type, score is not None]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        save_score(puck_id, game_type, score, session_id)
        return jsonify({
            'success': True,
            'message': 'Score saved',
            'puck_id': puck_id,
            'score': score
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def api_register_puck():
    """
    Register a puck

    POST /api/register
    {
        "puck_id": 1,
        "name": "Puck_1",
        "table_number": 1,
        "battery_level": 85
    }
    """
    data = request.get_json()

    puck_id = data.get('puck_id')
    name = data.get('name', f"Puck_{puck_id}")
    table_number = data.get('table_number', 1)
    battery_level = data.get('battery_level', 100)

    if not puck_id:
        return jsonify({'error': 'puck_id required'}), 400

    try:
        register_puck(puck_id, name, table_number, battery_level)

        # Broadcast new puck via WebSocket
        socketio.emit('puck_online', {
            'puck_id': puck_id,
            'name': name,
            'table_number': table_number
        })

        return jsonify({
            'success': True,
            'message': 'Puck registered',
            'puck_id': puck_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get overall stats"""
    ph = get_placeholder()

    pucks_result = execute_query(f'SELECT COUNT(*) as total_pucks FROM pucks WHERE is_online = {ph}', (True,), fetch_one=True)
    games_result = execute_query('SELECT COUNT(*) as total_games FROM games', fetch_one=True)
    score_result = execute_query('SELECT SUM(score) as total_score FROM games', fetch_one=True)

    return jsonify({
        'total_pucks': pucks_result['total_pucks'],
        'total_games': games_result['total_games'],
        'total_score': score_result['total_score'] or 0
    })

# ============================================================================
# NEW ROUTES - CUSTOMER DASHBOARD & MULTI-BAR
# ============================================================================

@app.route('/bar/<bar_slug>/table/<int:table_num>')
def customer_dashboard(bar_slug, table_num):
    """
    Customer-facing dashboard for game selection and play
    Accessed via QR code at each table
    """
    ph = get_placeholder()
    bar = execute_query(f'SELECT * FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return f"Bar '{bar_slug}' not found", 404

    return render_template('customer_dashboard_v2.html',
                          bar_name=bar['name'],
                          bar_slug=bar_slug,
                          table_number=table_num)

@app.route('/bar/<bar_slug>/table/<int:table_num>/skill')
def skill_games_dashboard(bar_slug, table_num):
    """
    51 Skill Games dashboard (original customer dashboard)
    """
    ph = get_placeholder()
    bar = execute_query(f'SELECT * FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return f"Bar '{bar_slug}' not found", 404

    return render_template('customer_dashboard.html',
                          bar_name=bar['name'],
                          bar_slug=bar_slug,
                          table_number=table_num)

@app.route('/bar/<bar_slug>/tv')
def bar_tv_dashboard(bar_slug):
    """
    TV display dashboard for bars
    Shows all tables, leaderboards, active games
    """
    ph = get_placeholder()
    bar = execute_query(f'SELECT * FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return f"Bar '{bar_slug}' not found", 404

    # TODO: Create bar_tv_dashboard.html template
    return render_template('leaderboard.html')  # Use existing for now

@app.route('/api/leaderboard/<bar_slug>')
def api_bar_leaderboard(bar_slug):
    """Get bar-specific leaderboard"""
    limit = request.args.get('limit', 10, type=int)
    ph = get_placeholder()

    # Get bar ID
    bar = execute_query(f'SELECT id FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return jsonify({'error': 'Bar not found'}), 404

    bar_id = bar['id']

    # Get leaderboard for this bar
    rows = execute_query(f'''SELECT * FROM leaderboard
                             WHERE bar_id = {ph}
                             ORDER BY total_score DESC
                             LIMIT {ph}''', (bar_id, limit), fetch_all=True)

    return jsonify(rows)

@app.route('/api/game-start', methods=['POST'])
def api_game_start():
    """
    Track when a game starts

    POST /api/game-start
    {
        "bar": "demo-bar",
        "table": 1,
        "puck_id": 1,
        "game_id": 41,
        "game_name": "Duck Hunt"
    }
    """
    data = request.get_json()

    bar_slug = data.get('bar')
    table_num = data.get('table')
    puck_id = data.get('puck_id')
    game_id = data.get('game_id')
    game_name = data.get('game_name')

    if not all([bar_slug, table_num, puck_id, game_id]):
        return jsonify({'error': 'Missing required fields'}), 400

    ph = get_placeholder()

    # Get bar ID
    bar = execute_query(f'SELECT id FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return jsonify({'error': 'Bar not found'}), 404

    bar_id = bar['id']

    # Clear any previous active games for this table
    execute_query(f'DELETE FROM active_games WHERE bar_id = {ph} AND table_number = {ph}',
                  (bar_id, table_num))

    # Insert new active game
    execute_query(f'''INSERT INTO active_games
                      (bar_id, table_number, puck_id, game_id, game_name)
                      VALUES ({ph}, {ph}, {ph}, {ph}, {ph})''',
                  (bar_id, table_num, puck_id, game_id, game_name))

    # Broadcast to bar TV
    socketio.emit('game_started', {
        'bar': bar_slug,
        'table': table_num,
        'game_id': game_id,
        'game_name': game_name
    })

    return jsonify({'success': True})

@app.route('/api/bars', methods=['GET', 'POST'])
def api_bars():
    """
    GET: List all bars
    POST: Create new bar
    """
    ph = get_placeholder()

    if request.method == 'GET':
        rows = execute_query(f'SELECT * FROM bars WHERE is_active = {ph}', (True,), fetch_all=True)
        return jsonify(rows)

    elif request.method == 'POST':
        data = request.get_json()

        name = data.get('name')
        slug = data.get('slug')
        location = data.get('location', '')
        total_tables = data.get('total_tables', 4)

        if not name or not slug:
            return jsonify({'error': 'Name and slug required'}), 400

        try:
            bar_id = execute_query(f'''INSERT INTO bars (name, slug, location, total_tables)
                                       VALUES ({ph}, {ph}, {ph}, {ph})''',
                                   (name, slug, location, total_tables))

            return jsonify({
                'success': True,
                'bar_id': bar_id,
                'name': name,
                'slug': slug
            })

        except Exception as e:
            # Check if it's a unique constraint violation
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                return jsonify({'error': 'Bar with this slug already exists'}), 400
            return jsonify({'error': str(e)}), 500

@app.route('/api/qr/<bar_slug>/<int:table_num>')
def api_generate_qr(bar_slug, table_num):
    """Generate QR code for a specific table"""
    import qrcode
    from io import BytesIO
    import base64

    # Generate URL
    url = f"http://tablewars.io/bar/{bar_slug}/table/{table_num}"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        'url': url,
        'qr_code': f"data:image/png;base64,{img_base64}",
        'bar': bar_slug,
        'table': table_num
    })

@app.route('/admin/qr-codes/<bar_slug>')
def admin_qr_codes(bar_slug):
    """Admin page to generate all QR codes for a bar"""
    ph = get_placeholder()
    bar = execute_query(f'SELECT * FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return f"Bar '{bar_slug}' not found", 404

    # TODO: Create admin QR code template
    return f"""
    <html>
    <head><title>QR Codes - {bar['name']}</title></head>
    <body style="font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px;">
        <h1>QR Codes for {bar['name']}</h1>
        <p>Generate QR codes for each table</p>
        <div id="qr-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
        </div>
        <script>
            const totalTables = {bar['total_tables']};
            const barSlug = '{bar_slug}';
            const qrGrid = document.getElementById('qr-grid');

            for (let i = 1; i <= totalTables; i++) {{
                fetch(`/api/qr/${{barSlug}}/${{i}}`)
                    .then(r => r.json())
                    .then(data => {{
                        const div = document.createElement('div');
                        div.style.border = '2px solid #333';
                        div.style.padding = '20px';
                        div.style.textAlign = 'center';
                        div.innerHTML = `
                            <h3>Table ${{i}}</h3>
                            <img src="${{data.qr_code}}" style="width: 200px; height: 200px;">
                            <p style="font-size: 12px; word-break: break-all;">${{data.url}}</p>
                            <button onclick="printTable(${{i}})">Print</button>
                        `;
                        qrGrid.appendChild(div);
                    }});
            }}

            function printTable(tableNum) {{
                window.print();
            }}
        </script>
    </body>
    </html>
    """

# ============================================================================
# CROSS-BAR COMPETITION ROUTES
# ============================================================================

@app.route('/api/leaderboard/global')
def api_global_leaderboard():
    """
    Global leaderboard across all bars

    Returns top players from all bars combined
    """
    limit = request.args.get('limit', 50, type=int)

    ph = get_placeholder()
    rows = execute_query(f'''SELECT * FROM leaderboard
                             ORDER BY total_score DESC
                             LIMIT {ph}''', (limit,), fetch_all=True)

    return jsonify(rows)

@app.route('/api/leaderboard/regional/<region>')
def api_regional_leaderboard(region):
    """
    Regional leaderboard for bars in a specific region

    Examples:
    - /api/leaderboard/regional/California
    - /api/leaderboard/regional/San%20Francisco,%20CA
    """
    limit = request.args.get('limit', 50, type=int)
    ph = get_placeholder()

    # Get bars in this region (case-insensitive LIKE search)
    rows = execute_query(f'''SELECT l.*
                             FROM leaderboard l
                             JOIN bars b ON l.bar_id = b.id
                             WHERE LOWER(b.location) LIKE LOWER({ph})
                             ORDER BY l.total_score DESC
                             LIMIT {ph}''',
                         (f'%{region}%', limit), fetch_all=True)

    return jsonify(rows)

@app.route('/api/bars/rankings')
def api_bar_rankings():
    """
    Bar rankings - which bars have the highest total scores

    Returns bars ranked by total scores of all their players
    """
    ph = get_placeholder()

    rows = execute_query(f'''SELECT
                                 b.id,
                                 b.name,
                                 b.slug,
                                 b.location,
                                 b.total_tables,
                                 COUNT(DISTINCT p.id) as total_players,
                                 COUNT(g.id) as total_games,
                                 COALESCE(SUM(g.score), 0) as total_score,
                                 COALESCE(AVG(g.score), 0) as avg_score,
                                 MAX(g.score) as high_score
                             FROM bars b
                             LEFT JOIN pucks p ON b.id = p.bar_id
                             LEFT JOIN games g ON p.id = g.puck_id
                             WHERE b.is_active = {ph}
                             GROUP BY b.id, b.name, b.slug, b.location, b.total_tables
                             ORDER BY total_score DESC''',
                         (True,), fetch_all=True)

    return jsonify(rows)

@app.route('/api/bars/<bar_slug>/stats')
def api_bar_stats(bar_slug):
    """
    Detailed stats for a specific bar
    """
    ph = get_placeholder()

    # Get bar info
    bar = execute_query(f'SELECT * FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return jsonify({'error': 'Bar not found'}), 404

    bar_id = bar['id']

    # Get bar stats
    stats = execute_query(f'''SELECT
                                  COUNT(DISTINCT p.id) as total_players,
                                  COUNT(g.id) as total_games,
                                  COALESCE(SUM(g.score), 0) as total_score,
                                  COALESCE(AVG(g.score), 0) as avg_score,
                                  MAX(g.score) as high_score,
                                  COUNT(DISTINCT DATE(g.timestamp)) as days_active
                              FROM pucks p
                              LEFT JOIN games g ON p.id = g.puck_id
                              WHERE p.bar_id = {ph}''',
                          (bar_id,), fetch_one=True)

    # Get top players at this bar
    top_players = execute_query(f'''SELECT * FROM leaderboard
                                    WHERE bar_id = {ph}
                                    ORDER BY total_score DESC
                                    LIMIT 10''',
                                (bar_id,), fetch_all=True)

    return jsonify({
        'bar': bar,
        'stats': stats,
        'top_players': top_players
    })

@app.route('/api/tournaments', methods=['GET'])
def api_tournaments():
    """
    List active tournaments (future feature)

    This endpoint is a placeholder for tournament support
    """
    return jsonify({
        'tournaments': [],
        'message': 'Tournament system coming soon!'
    })

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Client connected"""
    print('🔌 Client connected')
    emit('connected', {'message': 'Connected to TABLE WARS server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected"""
    print('🔌 Client disconnected')

@socketio.on('request_leaderboard')
def handle_leaderboard_request():
    """Client requested leaderboard"""
    emit('leaderboard_update', get_leaderboard())

# ============================================================================
# GAME GALLERY
# ============================================================================

@app.route('/games')
def game_gallery():
    """Browse all available TV games"""
    return render_template('game_gallery.html')

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════╗")
    print("║   TABLE WARS - Scoreboard Server v1.0    ║")
    print("╚═══════════════════════════════════════════╝\n")

    init_database()
    init_trivia_database()
    seed_trivia_data()

    # Check if we need to seed questions
    question_count = execute_query('SELECT COUNT(*) as count FROM trivia_questions', fetch_one=True)
    if question_count['count'] == 0:
        print("📝 Seeding sample trivia questions...")
        seed_questions()

    init_trivia_routes(app, socketio)
    init_tv_game_routes(app, socketio)
    init_multiplayer_routes(app, socketio)
    init_firmware_routes(app)  # NEW: OTA firmware updates

    print("🚀 Starting server...")
    print("📊 Leaderboard: http://localhost:5001")
    print("🎭 Admin Dashboard: http://localhost:5001/admin")
    print("📡 API Docs: http://localhost:5001/api/stats")
    print("🎮 TV Games (52-56): http://localhost:5001/tv/puck-racer/1")
    print("🔧 Firmware Dashboard: http://localhost:5001/firmware/dashboard")  # NEW
    print("\n⏸️  Press Ctrl+C to stop\n")

    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)

# Game gallery route
@app.route('/games')
def game_gallery():
    return render_template('game_gallery.html')
