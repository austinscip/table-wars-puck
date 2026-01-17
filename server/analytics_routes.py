"""
Flask Routes for Analytics Dashboard
Bar owner insights, metrics, and reporting

Sprint 1B: Analytics Dashboard
"""

from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
from database import execute_query, get_placeholder
import json

analytics_bp = Blueprint('analytics', __name__)

# ============================================================================
# ANALYTICS DATA AGGREGATION
# ============================================================================

def get_bar_overview(bar_slug, days=7):
    """
    Get overview metrics for a bar

    Returns:
    - Total games played
    - Unique players
    - Total revenue potential (based on game count)
    - Player engagement metrics
    """
    ph = get_placeholder()

    # Get bar ID
    bar = execute_query(f'SELECT id FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return None

    bar_id = bar['id']

    # Date range
    start_date = datetime.now() - timedelta(days=days)

    # Total games in period
    games_query = f'''SELECT COUNT(*) as total_games,
                            COALESCE(SUM(score), 0) as total_score,
                            COALESCE(AVG(score), 0) as avg_score
                      FROM games g
                      JOIN pucks p ON g.puck_id = p.id
                      WHERE p.bar_id = {ph}
                      AND g.timestamp >= {ph}'''

    games_stats = execute_query(games_query, (bar_id, start_date), fetch_one=True)

    # Unique players (unique puck IDs)
    players_query = f'''SELECT COUNT(DISTINCT p.id) as unique_players
                        FROM pucks p
                        WHERE p.bar_id = {ph}
                        AND p.last_seen >= {ph}'''

    players_stats = execute_query(players_query, (bar_id, start_date), fetch_one=True)

    # Games by day
    daily_query = f'''SELECT DATE(g.timestamp) as game_date,
                            COUNT(*) as game_count
                      FROM games g
                      JOIN pucks p ON g.puck_id = p.id
                      WHERE p.bar_id = {ph}
                      AND g.timestamp >= {ph}
                      GROUP BY DATE(g.timestamp)
                      ORDER BY game_date DESC'''

    daily_games = execute_query(daily_query, (bar_id, start_date), fetch_all=True)

    # Peak hours (hour of day analysis)
    peak_hours_query = f'''SELECT EXTRACT(HOUR FROM g.timestamp) as hour,
                                  COUNT(*) as game_count
                           FROM games g
                           JOIN pucks p ON g.puck_id = p.id
                           WHERE p.bar_id = {ph}
                           AND g.timestamp >= {ph}
                           GROUP BY EXTRACT(HOUR FROM g.timestamp)
                           ORDER BY game_count DESC
                           LIMIT 5'''

    peak_hours = execute_query(peak_hours_query, (bar_id, start_date), fetch_all=True)

    # Revenue potential (assume $1 per game)
    revenue_potential = games_stats['total_games'] * 1.0

    return {
        'total_games': games_stats['total_games'],
        'unique_players': players_stats['unique_players'],
        'total_score': games_stats['total_score'],
        'avg_score': games_stats['avg_score'],
        'revenue_potential': revenue_potential,
        'daily_breakdown': daily_games,
        'peak_hours': peak_hours,
        'period_days': days
    }


def get_game_popularity(bar_slug, days=7):
    """Get most popular games at this bar"""
    ph = get_placeholder()

    bar = execute_query(f'SELECT id FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return None

    bar_id = bar['id']
    start_date = datetime.now() - timedelta(days=days)

    query = f'''SELECT g.game_type,
                       COUNT(*) as play_count,
                       COALESCE(AVG(g.score), 0) as avg_score,
                       MAX(g.score) as high_score
                FROM games g
                JOIN pucks p ON g.puck_id = p.id
                WHERE p.bar_id = {ph}
                AND g.timestamp >= {ph}
                GROUP BY g.game_type
                ORDER BY play_count DESC'''

    return execute_query(query, (bar_id, start_date), fetch_all=True)


def get_player_engagement(bar_slug, days=7):
    """Get player engagement metrics"""
    ph = get_placeholder()

    bar = execute_query(f'SELECT id FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return None

    bar_id = bar['id']
    start_date = datetime.now() - timedelta(days=days)

    # Get session data (approximate with time gaps)
    query = f'''SELECT p.id as puck_id,
                       p.name,
                       COUNT(*) as total_games,
                       COALESCE(SUM(g.score), 0) as total_score,
                       MIN(g.timestamp) as first_play,
                       MAX(g.timestamp) as last_play
                FROM pucks p
                LEFT JOIN games g ON p.id = g.puck_id
                WHERE p.bar_id = {ph}
                AND g.timestamp >= {ph}
                GROUP BY p.id, p.name
                ORDER BY total_games DESC
                LIMIT 20'''

    top_players = execute_query(query, (bar_id, start_date), fetch_all=True)

    # Calculate engagement score (games per day)
    for player in top_players:
        if player['first_play'] and player['last_play']:
            days_active = (player['last_play'] - player['first_play']).days + 1
            player['games_per_day'] = player['total_games'] / max(days_active, 1)
            player['engagement_score'] = round(player['games_per_day'] * 10, 1)

    return top_players


def get_connection_health_history(bar_slug, hours=24):
    """Get connection health metrics over time"""
    # TODO: Implement once we start storing health metrics in DB
    # For now, return placeholder
    return {
        'avg_latency': 45,  # ms
        'packet_loss_rate': 2.3,  # %
        'disconnections': 5,
        'uptime_percent': 97.7
    }


# ============================================================================
# REST API ROUTES
# ============================================================================

@analytics_bp.route('/api/analytics/bar/<bar_slug>/overview', methods=['GET'])
def api_bar_overview(bar_slug):
    """
    Get bar overview analytics
    GET /api/analytics/bar/demo-bar/overview?days=7
    """
    days = request.args.get('days', 7, type=int)

    overview = get_bar_overview(bar_slug, days)

    if not overview:
        return jsonify({'error': 'Bar not found'}), 404

    return jsonify(overview)


@analytics_bp.route('/api/analytics/bar/<bar_slug>/games', methods=['GET'])
def api_game_popularity(bar_slug):
    """
    Get game popularity rankings
    GET /api/analytics/bar/demo-bar/games?days=7
    """
    days = request.args.get('days', 7, type=int)

    games = get_game_popularity(bar_slug, days)

    if games is None:
        return jsonify({'error': 'Bar not found'}), 404

    return jsonify({'games': games})


@analytics_bp.route('/api/analytics/bar/<bar_slug>/players', methods=['GET'])
def api_player_engagement(bar_slug):
    """
    Get player engagement metrics
    GET /api/analytics/bar/demo-bar/players?days=7
    """
    days = request.args.get('days', 7, type=int)

    players = get_player_engagement(bar_slug, days)

    if players is None:
        return jsonify({'error': 'Bar not found'}), 404

    return jsonify({'players': players})


@analytics_bp.route('/api/analytics/bar/<bar_slug>/health', methods=['GET'])
def api_connection_health(bar_slug):
    """
    Get connection health history
    GET /api/analytics/bar/demo-bar/health?hours=24
    """
    hours = request.args.get('hours', 24, type=int)

    health = get_connection_health_history(bar_slug, hours)

    return jsonify(health)


@analytics_bp.route('/api/analytics/bar/<bar_slug>/export', methods=['GET'])
def api_export_data(bar_slug):
    """
    Export analytics data as CSV
    GET /api/analytics/bar/demo-bar/export?format=csv&days=30
    """
    days = request.args.get('days', 30, type=int)
    format_type = request.args.get('format', 'csv')

    overview = get_bar_overview(bar_slug, days)

    if not overview:
        return jsonify({'error': 'Bar not found'}), 404

    if format_type == 'csv':
        # Generate CSV
        csv_data = f"Date,Games Played,Revenue Potential\n"
        for day in overview['daily_breakdown']:
            csv_data += f"{day['game_date']},{day['game_count']},${day['game_count']}\n"

        from flask import Response
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=analytics_{bar_slug}_{days}days.csv'}
        )

    elif format_type == 'json':
        return jsonify(overview)

    else:
        return jsonify({'error': 'Invalid format. Use csv or json'}), 400


# ============================================================================
# DASHBOARD UI ROUTE
# ============================================================================

@analytics_bp.route('/admin/analytics/<bar_slug>')
def analytics_dashboard(bar_slug):
    """Bar owner analytics dashboard"""
    ph = get_placeholder()
    bar = execute_query(f'SELECT * FROM bars WHERE slug = {ph}', (bar_slug,), fetch_one=True)

    if not bar:
        return f"Bar '{bar_slug}' not found", 404

    return render_template('analytics_dashboard.html', bar=bar, bar_slug=bar_slug)


def init_analytics_routes(app):
    """Initialize analytics routes"""
    app.register_blueprint(analytics_bp)
    print("✅ Analytics routes registered")
    print("   Endpoints:")
    print("   - GET /api/analytics/bar/<slug>/overview")
    print("   - GET /api/analytics/bar/<slug>/games")
    print("   - GET /api/analytics/bar/<slug>/players")
    print("   - GET /api/analytics/bar/<slug>/health")
    print("   - GET /api/analytics/bar/<slug>/export")
    print("   - GET /admin/analytics/<slug> (Dashboard)")
