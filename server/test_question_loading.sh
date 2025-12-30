#!/bin/bash

# Create session
RESPONSE=$(curl -s -X POST http://localhost:5001/api/trivia/start \
  -H "Content-Type: application/json" \
  -d '{"bar_slug":"demo-bar","table_number":1,"game_type":"category_royale","players":[{"puck_id":"puck_1","player_name":"Player 1"}]}')

echo "Create session response:"
echo "$RESPONSE" | python3 -m json.tool

# Extract session code
SESSION_CODE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_code'])")

echo ""
echo "Session code: $SESSION_CODE"
echo ""
echo "Loading question..."
echo ""

# Load question
curl -s -X GET "http://localhost:5001/api/trivia/question/$SESSION_CODE" | python3 -m json.tool
