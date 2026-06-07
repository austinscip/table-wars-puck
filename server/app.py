"""
TABLE WARS - Web Scoreboard Server
Flask + WebSocket server for real-time leaderboard

Run with: python app.py
Access at: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
from markupsafe import escape
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime
import json
import os

# Sprint 1E: Load environment variables from .env file (if present)
from dotenv import load_dotenv
load_dotenv()

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
from pair_routes import init_pair_routes
from trivia_database import init_trivia_database, seed_trivia_data
from trivia_questions_seed import seed_questions

# Import TV game routes
from tv_game_routes import init_tv_game_routes

# Import multiplayer game routes
from multiplayer_routes import init_multiplayer_routes

# Import firmware OTA routes
from firmware_routes import init_firmware_routes

# Import analytics routes
from analytics_routes import init_analytics_routes

# Admin auth gate (audit 0.1)
from admin_auth import require_admin

app = Flask(__name__)

# Sprint 1E: Use environment variables for production configuration.
# SECRET_KEY: never ship the hardcoded dev constant to a real deploy — a known
# signing key lets anyone forge Flask-signed cookies. Nothing here uses the
# Flask session for AUTH (the admin gate is a bearer token, not a cookie), so a
# random per-process key when the env is unset is both safe and strictly better
# than a public constant (audit legacy-flask-2026-06-06).
import secrets as _secrets
_secret = os.environ.get('SECRET_KEY')
if not _secret:
    _secret = _secrets.token_hex(32)
    _BOOT_SECRET_WARNING = True  # logged once the logger is up (below)
else:
    _BOOT_SECRET_WARNING = False
app.config['SECRET_KEY'] = _secret
# Defense-in-depth cookie flags (no auth cookie exists today, but harmless and
# correct). SECURE is left off so the LAN http deployment keeps working.
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
# CORS: lock to explicit origins in prod via CORS_ALLOWED_ORIGINS
# (comma-separated). Defaults to '*' for dev — the portal is a separate
# origin, so set this to the portal/TV origins before going live.
_cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '*').strip()
if _cors_origins and _cors_origins != '*':
    _cors_list = [o.strip() for o in _cors_origins.split(',') if o.strip()]
    CORS(app, origins=_cors_list)
else:
    _cors_list = '*'  # dev: allow all
    CORS(app)  # dev: allow all

# Structured logging + optional Sentry for the runtime AND this Flask app.
# When SENTRY_DSN is set (and sentry-sdk is installed) Sentry auto-
# instruments Flask + the logging path, so the error handler below and any
# logger.exception() ship off-box; otherwise both no-op cleanly.
from runtime import configure_logging, init_sentry, init_analytics, get_logger
configure_logging()
init_sentry()
init_analytics()  # PostHog product analytics — dormant unless POSTHOG_API_KEY set
_flask_log = get_logger("flask")
# async_mode='threading' avoids the werkzeug websocket-upgrade quirk
# on Python 3.14 dev server ("write() before start_response"). It also
# eliminates the noisy 500 in logs when the client opens a websocket.
# Production runs under gunicorn + the gevent worker (GeventWebSocketWorker,
# see deploy/). NOT eventlet — that dependency was unused and dropped in the
# 2026-06-06 deps audit.
# logger=False/engineio_logger=False mute the warning chatter.
# Drive the websocket CORS from the SAME env as the HTTP CORS above — it used
# to be hardcoded "*", so the socket accepted connections from ANY origin even
# when the HTTP API was locked down (audit legacy-flask-2026-06-06).
socketio = SocketIO(
    app,
    cors_allowed_origins=_cors_list,
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)
if _BOOT_SECRET_WARNING:
    _flask_log.warning(
        "SECRET_KEY unset — using a random per-process key. Set SECRET_KEY in "
        "the environment for stable signing across restarts/workers."
    )


# Slice I — robustness: any uncaught exception returns a structured
# back-off body instead of Flask's default 500 HTML page. Pucks that
# poll on a tight 500ms cadence (current-question / match-state) would
# otherwise hammer a wedged server. `retry_in_ms` tells the puck firmware
# how long to wait before the next poll. Status 503 is more accurate
# than 500 for "service temporarily unavailable, retry."
@app.errorhandler(Exception)
def _robust_exception_handler(e):
    # Pass through Flask's own HTTPException (404, 405, etc.) — those
    # carry intentional status codes, not server crashes.
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    # Structured log with traceback — captured by Sentry's logging
    # integration when configured, and visible in dev either way.
    _flask_log.exception(
        "unhandled error on %s %s", request.method, request.path
    )
    return jsonify({
        "error": "server",
        "message": "transient server error, retry",
        "retry_in_ms": 2000,
    }), 503

# Sprint 1E: Database and route initialization moved to bottom of file (after function definitions)

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
@require_admin()
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
    # silent=True: a missing/204 Content-Type or malformed body yields None
    # instead of raising — otherwise trivially-malformed input becomes a 503
    # that the puck's tight poll loop retries into a storm.
    data = request.get_json(silent=True)

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    game_type = data.get('game_type')

    # Coerce + bound the numerics so a non-numeric or absurd value can't 500
    # the save path or poison the leaderboard (audit legacy-flask-2026-06-06).
    try:
        puck_id = int(data['puck_id'])
        score = int(data['score'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'puck_id and score must be integers'}), 400
    if not game_type or not isinstance(game_type, str):
        return jsonify({'error': 'game_type required'}), 400
    if not (0 <= score <= 1_000_000):
        return jsonify({'error': 'score out of range [0, 1000000]'}), 400

    session_id = data.get('session_id')
    if session_id is not None and not isinstance(session_id, str):
        return jsonify({'error': 'session_id must be a string'}), 400

    try:
        save_score(puck_id, game_type, score, session_id)
        return jsonify({
            'success': True,
            'message': 'Score saved',
            'puck_id': puck_id,
            'score': score
        })
    except Exception:
        # Don't leak the exception detail to the caller; the global handler /
        # Sentry capture the traceback server-side.
        _flask_log.exception("save_score failed")
        return jsonify({'error': 'could not save score'}), 500

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
        return f"Bar '{escape(bar_slug)}' not found", 404

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
        return f"Bar '{escape(bar_slug)}' not found", 404

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
        return f"Bar '{escape(bar_slug)}' not found", 404

    return render_template('bar_tv_dashboard.html', bar=bar)

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

@app.route('/api/admin/bars/<bar_slug>/pucks', methods=['POST'])
@require_admin()
def api_register_puck_to_bar(bar_slug):
    """Slice J — bar deployment. Register a puck to a venue + table so
    the puck shows up under that bar's leaderboard / dashboard. Used
    once per puck on initial install. Idempotent: re-posting updates
    the table assignment.

    Body: {puck_id: int, table_number: int, name?: str}
    """
    ph = get_placeholder()
    data = request.get_json(silent=True) or {}
    try:
        puck_id = int(data.get('puck_id'))
        table_number = int(data.get('table_number'))
    except (TypeError, ValueError):
        return jsonify({'error': 'puck_id and table_number required'}), 400

    bar = execute_query(f'SELECT id, name, total_tables FROM bars WHERE slug = {ph}',
                        (bar_slug,), fetch_one=True)
    if not bar:
        return jsonify({'error': f"bar '{bar_slug}' not found"}), 404
    if table_number < 1 or table_number > bar['total_tables']:
        return jsonify({
            'error': f"table_number {table_number} out of range "
                     f"(bar has {bar['total_tables']} tables)"
        }), 400

    name = data.get('name') or f"Puck_{puck_id}"
    # register_puck upserts.
    register_puck(puck_id, name, table_number)
    # Pin bar_id on the puck row if the schema has the column.
    try:
        execute_query(
            f'UPDATE pucks SET bar_id = {ph} WHERE id = {ph}',
            (bar['id'], puck_id),
        )
    except Exception as e:
        # Older schemas may not have bar_id on pucks; fail soft so the
        # endpoint still answers without a 500.
        _flask_log.warning("register_puck_to_bar: bar_id update skipped: %s", e)

    return jsonify({
        'ok': True,
        'puck_id': puck_id,
        'bar_slug': bar_slug,
        'bar_name': bar['name'],
        'table_number': table_number,
    })


@app.route('/admin/qr-codes/<bar_slug>')
@require_admin()
def admin_qr_codes(bar_slug):
    """Admin page to generate all QR codes for a bar"""
    ph = get_placeholder()
    bar = execute_query(f'SELECT * FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return f"Bar '{escape(bar_slug)}' not found", 404

    return render_template('admin_qr_codes.html', bar=bar)

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

def register_core_socketio_handlers(sio):
    """Register core WebSocket handlers - called from main"""
    # Note: puck_input handler is in tv_game_routes.py to avoid conflicts
    from flask_socketio import join_room, leave_room

    @sio.on("join_pair_room")
    def _on_join_pair_room(data):
        """TV view subscribes to a pair_code room to mirror dial progress
        and receive the 'paired' event when the puck confirms."""
        code = (data or {}).get("pair_code")
        if isinstance(code, str) and len(code) == 6 and code.isdigit():
            join_room(code)
            sio.emit("joined_pair_room", {"pair_code": code}, room=code)

    @sio.on("leave_pair_room")
    def _on_leave_pair_room(data):
        code = (data or {}).get("pair_code")
        if isinstance(code, str):
            leave_room(code)

    @sio.on("join_session_room")
    def _on_join_session_room(data):
        """TV view re-subscribes to a session_code room after pairing,
        so it receives question_show / answer_locked / reveal /
        match_ended events emitted from trivia_routes."""
        code = (data or {}).get("session_code")
        if isinstance(code, str) and code:
            join_room(code)
            sio.emit("joined_session_room", {"session_code": code}, room=code)

    @sio.on("join_lobby")
    def _on_join_lobby(*_args):
        """Title-screen browsers join 'lobby' so they get notified when
        any puck POSTs /api/pair/request — then they auto-advance to
        that puck's pair page. Accepts *args so it works whether the
        client emits with or without a payload."""
        join_room("lobby")

    _flask_log.info("core WebSocket handlers registered")

# ============================================================================
# GAME GALLERY
# ============================================================================

@app.route('/games')
def game_gallery():
    """Browse all available TV games"""
    return render_template('game_gallery.html')


@app.route('/test/puck-simulator')
def puck_simulator():
    """Test tool for simulating puck input without physical hardware"""
    return render_template('test_puck_simulator.html')

@app.route('/test/sensor-validation')
def sensor_validation():
    """Combined sensor simulator and debug panel for validation"""
    return render_template('test_sensor_validation.html')

# ============================================================================
# SPEED PYRAMID v1 (Vite + React + Tailwind + Framer Motion)
# Serves the SPA bundle at server/static/games/speed-pyramid/dist/ for
# any /tv/speed-pyramid/* path. Vite was built with base='./' so the
# index.html references assets relatively; Flask's existing /static
# handler picks them up via the dist/assets/ path.
# ============================================================================

import os
from flask import send_from_directory

SPEED_PYRAMID_DIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static', 'games', 'speed-pyramid', 'dist'
)

@app.route('/tv/speed-pyramid')
@app.route('/tv/speed-pyramid/')
@app.route('/tv/speed-pyramid/<path:subpath>')
def speed_pyramid_app(subpath: str | None = None):
    """Serve the Speed Pyramid v1 React SPA. SPA fallback: any unknown
    subpath returns index.html so client-side react-router-dom can
    resolve it. Asset requests (CSS/JS/svg/audio) hit the static file
    branch below."""
    if subpath and not subpath.endswith('/'):
        candidate = os.path.join(SPEED_PYRAMID_DIST, subpath)
        if os.path.isfile(candidate):
            return send_from_directory(SPEED_PYRAMID_DIST, subpath)
    return _serve_tv_index()


def _serve_tv_index():
    """Serve the SPA index, injecting the operator token (when SP_OPERATOR_TOKEN
    is set) as a meta tag the TV reads to authenticate its control-plane calls
    (force-reveal / start-timer / minigame-finish / reset). The token only
    reaches a client that loads the actual TV page, not a blind script — the
    realistic griefing vector. When the env is unset, serve the static file
    unchanged (dev fast path)."""
    op = os.environ.get('SP_OPERATOR_TOKEN')
    index_path = os.path.join(SPEED_PYRAMID_DIST, 'index.html')
    if not op or not os.path.isfile(index_path):
        return send_from_directory(SPEED_PYRAMID_DIST, 'index.html')
    try:
        from markupsafe import escape
        with open(index_path, 'r', encoding='utf-8') as f:
            html = f.read()
        meta = f'<meta name="sp-operator-token" content="{escape(op)}">'
        html = html.replace('<head>', '<head>' + meta, 1) if '<head>' in html \
            else meta + html
        resp = app.make_response(html)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        return resp
    except OSError:
        return send_from_directory(SPEED_PYRAMID_DIST, 'index.html')

# ============================================================================
# MAIN
# ============================================================================

# Sprint 1E: Initialize database and routes at module level (for gunicorn)
# This code runs when the module is imported, ensuring everything is ready for gunicorn workers
init_database()
init_trivia_database()
seed_trivia_data()

# Check if we need to seed questions
question_count = execute_query('SELECT COUNT(*) as count FROM trivia_questions', fetch_one=True)
if question_count and question_count['count'] == 0:
    from trivia_questions_seed import seed_questions
    seed_questions()

# Initialize all route handlers
register_core_socketio_handlers(socketio)
init_trivia_routes(app, socketio)
init_tv_game_routes(app, socketio)
init_multiplayer_routes(app, socketio)
init_firmware_routes(app)
init_analytics_routes(app)
init_pair_routes(app, socketio)  # Speed Pyramid v1 — pair-code flow

# Track G multi-game runtime. Mounts /api/runtime/* alongside the
# Speed Pyramid v1 /api/pair/* flow so the cut-over is non-disruptive.
# init_runtime_routes also wires the local-first TV path (ADR 0004): the
# MatchManager pushes each frame to a per-match SocketIO room the TV joins.
from runtime_routes import init_runtime_routes
init_runtime_routes(app, socketio)

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

    # Route handlers + socketio handlers are registered at module level
    # above (lines ~714-719) so they're attached whether app.py is run
    # directly or imported by gunicorn. The duplicate calls that used to
    # live here caused trivia_bp ValueError on local startup.

    print("🚀 Starting server...")
    print("📊 Leaderboard: http://localhost:5001")
    print("🎭 Admin Dashboard: http://localhost:5001/admin")
    print("📡 API Docs: http://localhost:5001/api/stats")
    print("🎮 TV Games (52-56): http://localhost:5001/tv/puck-racer/1")
    print("🔧 Firmware Dashboard: http://localhost:5001/firmware/dashboard")
    print("📈 Analytics: http://localhost:5001/admin/analytics/<bar-slug>")  # NEW
    print("\n⏸️  Press Ctrl+C to stop\n")

    # Sprint 1E: Use environment variables for production configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5001))
    # Default OFF: the Werkzeug debugger is an RCE console if exposed, and this
    # box can be internet-facing (Railway/nginx). Opt IN with DEBUG=true for
    # local dev (audit legacy-flask-2026-06-06).
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    # Slice J — bar deployment. Advertise via mDNS so pucks find the
    # server as `tablewars-server.local` (or `<instance>.local` if
    # SP_MDNS_INSTANCE is set per venue) without a firmware rebuild.
    # Sandbox + prod can coexist on the same LAN if they use different
    # instances (e.g. SP_MDNS_INSTANCE=tablewars-sandbox).
    # Set SP_MDNS_DISABLE=1 to skip — useful on locked-down networks
    # or under Flask debug reloader (the child process duplicates the
    # registration; either disable or accept the unregister-replace).
    if os.environ.get("SP_MDNS_DISABLE") != "1":
        try:
            from mdns_advertise import advertise_mdns
            instance = os.environ.get("SP_MDNS_INSTANCE",
                                      "tablewars-server")
            advertise_mdns(port=port, instance=instance)
        except Exception as e:  # noqa: BLE001
            _flask_log.warning("mDNS advertise failed: %s", e)

    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
