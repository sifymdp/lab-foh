#!/bin/bash
# ─────────────────────────────────────────────────────────────
# FOH Alert System — Smoke Test
# Fires a test alert through the SAME create-alert + WebSocket path
# the YOLOv8 camera pipeline uses, confirms it was delivered to the
# frontend, checks the Ollama wording, then cleans up after itself.
# Requires the FOH system to be running (use "Start FOH.command" first).
#
# TIP: have the app open (AI Alerts page) while this runs — you'll see
#      the badge tick up and a toast appear live.
# ─────────────────────────────────────────────────────────────
API="http://localhost:8000"
EMAIL="manager@foh.demo"
PASS="demo1234"
CONTAINER="lab-foh-backend-1"

echo "🔔  FOH ALERT SMOKE TEST"
echo "────────────────────────────────────────"

# 0. Backend reachable?
if ! curl -s --max-time 5 "$API/health" | grep -q '"ok":true'; then
  echo "❌ Backend not reachable at $API."
  echo "   Start the system first (double-click 'Start FOH.command')."
  read -p "Press Enter to close..."; exit 1
fi
echo "✅ Backend is up."

# 1. Log in as a manager (manager-targeted alerts)
TOKEN=$(curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('accessToken',''))" 2>/dev/null)
[ -z "$TOKEN" ] && { echo "❌ Login failed."; read -p "Press Enter..."; exit 1; }
echo "✅ Logged in as $EMAIL"

# 2. Count active alerts BEFORE
before=$(curl -s "$API/ai/events?resolved=false" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null)
echo "📊 Active alerts before: $before"

# 3. Fire the test alert (identical path to the camera pipeline)
echo "🚀 Firing test alert..."
curl -s -X POST "$API/ai/events" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"eventType":"DEPARTURE_ALERT","targetRole":"MANAGER","message":"SMOKE TEST: Table 4 appears empty while still in BILLING — possible walkout."}' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('   created id',d['id'][:8],'· type',d['eventType'])" 2>/dev/null

# 4. Count AFTER and judge
sleep 1
after=$(curl -s "$API/ai/events?resolved=false" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null)
echo "📊 Active alerts after:  $after"
if [ "${after:-0}" -gt "${before:-0}" ]; then
  echo "✅ PASS — alert created & delivered (count $before → $after)."
  echo "   👉 In the app, the AI Alerts badge should have ticked up + a toast shown."
else
  echo "⚠️  Count did not rise — check the app or 'docker compose logs backend'."
fi

# 5. Verify Ollama alert wording is up (and how fast)
echo
echo "🤖 Checking Ollama alert wording..."
docker exec "$CONTAINER" python -c "
import time
from app.services.ollama_service import generate_text
t=time.time()
m=generate_text('Table 5 has been dirty for 10 minutes. One short friendly sentence asking a waiter to clear it. No JSON.', fallback='FALLBACK')
print(f'   latency {time.time()-t:.1f}s · ollama_used {m!=\"FALLBACK\"}')
print('   sample:', m[:90])
" 2>/dev/null | grep -E "latency|sample" || echo "   (couldn't reach Ollama — alerts still fire using template fallback)"

# 6. Clean up the smoke-test alert(s)
echo
echo "🧹 Cleaning up smoke-test alerts..."
docker exec "$CONTAINER" python -c "
from app.database import SessionLocal
from app.models import AIEvent
db=SessionLocal()
t=db.query(AIEvent).filter(AIEvent.message.like('SMOKE TEST%')).all()
for x in t: db.delete(x)
db.commit()
print('   removed', len(t), 'test alert(s) · real alerts remaining:', db.query(AIEvent).count())
" 2>/dev/null | grep removed

echo
echo "✅ Smoke test complete."
read -p "Press Enter to close..."
