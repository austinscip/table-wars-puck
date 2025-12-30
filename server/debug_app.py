#!/usr/bin/env python3
"""
Debug wrapper for Flask app - adds detailed error logging
"""

import sys
sys.path.insert(0, '/Users/austinscipione/table-wars-puck/server')

from app import app, socketio, init_database
import traceback

# Monkey-patch the save_score function to add debug logging
import app as app_module
original_save_score = app_module.save_score

def debug_save_score(puck_id, game_type, score, session_id=None):
    """Wrapped save_score with debug logging"""
    print(f"\n🐛 DEBUG save_score called:")
    print(f"   puck_id: {puck_id} (type: {type(puck_id)})")
    print(f"   game_type: {game_type} (type: {type(game_type)})")
    print(f"   score: {score} (type: {type(score)})")
    print(f"   session_id: {session_id} (type: {type(session_id)})")

    try:
        result = original_save_score(puck_id, game_type, score, session_id)
        print(f"✅ save_score succeeded")
        return result
    except Exception as e:
        print(f"❌ save_score error: {e}")
        print(f"   Full traceback:")
        traceback.print_exc()
        raise

app_module.save_score = debug_save_score

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════╗")
    print("║   TABLE WARS - DEBUG MODE                ║")
    print("╚═══════════════════════════════════════════╝\n")

    init_database()

    print("🐛 Debug mode enabled - detailed error logging")
    print("🚀 Starting server on http://localhost:5001")
    print("\n⏸️  Press Ctrl+C to stop\n")

    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
