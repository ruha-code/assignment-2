"""
Orbit Control — Flask API Backend
Satellite Launch Management System
"""
 
from flask import Flask, jsonify, request, send_from_directory
import json, os, sys
from datetime import datetime
 
# Always resolve paths relative to this script's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
 
app = Flask(__name__, static_folder=STATIC_DIR)
 
DB_FILE  = os.path.join(BASE_DIR, "satellites_db.json")
LOG_FILE = os.path.join(BASE_DIR, "log.txt")
STAGES   = ["Assembled", "Testing", "Launched"]
STAGE_INDEX = {s: i for i, s in enumerate(STAGES)}
_cache: dict = {}
 
# ── Logging ──────────────────────────────────────────────────
def log(action: str, detail: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {action}"
    if detail:
        line += f" | {detail}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
 
# ── DB ───────────────────────────────────────────────────────
def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
 
def save_db(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
 
# ── Cache ────────────────────────────────────────────────────
def get_satellite(sat_id: str):
    if sat_id in _cache:
        log("CACHE HIT", f"id={sat_id}")
        return _cache[sat_id], "cache"
    db = load_db()
    if sat_id not in db:
        return None, None
    _cache[sat_id] = db[sat_id]
    log("CACHE MISS", f"id={sat_id}")
    return db[sat_id], "file"
 
def invalidate(sat_id: str):
    _cache.pop(sat_id, None)
 
# ── Routes ───────────────────────────────────────────────────
 
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")
 
@app.route("/api/satellites", methods=["GET"])
def list_satellites():
    stage = request.args.get("stage", "").strip()
    db = load_db()
    sats = list(db.values())
    if stage:
        sats = [s for s in sats if s["stage"].lower() == stage.lower()]
    log("LIST", f"stage_filter={stage or 'none'} count={len(sats)}")
    return jsonify(sats)
 
@app.route("/api/satellites/<sat_id>", methods=["GET"])
def view_satellite(sat_id):
    sat, source = get_satellite(sat_id.upper())
    if sat is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify({**sat, "_source": source})
 
@app.route("/api/satellites", methods=["POST"])
def create_satellite():
    data = request.json
    name     = (data.get("name") or "").strip()
    mission  = (data.get("mission") or "").strip()
    operator = (data.get("operator") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
 
    db = load_db()
    sat_id = f"SAT-{len(db) + 1:04d}"
    ts = datetime.now().isoformat()
    sat = {
        "id": sat_id, "name": name, "mission": mission,
        "operator": operator, "stage": "Assembled",
        "history": [{"stage": "Assembled", "timestamp": ts}]
    }
    db[sat_id] = sat
    save_db(db)
    invalidate(sat_id)
    log("CREATE", f"id={sat_id} name={name!r}")
    return jsonify(sat), 201
 
@app.route("/api/satellites/<sat_id>/advance", methods=["POST"])
def advance_satellite(sat_id):
    sat, _ = get_satellite(sat_id.upper())
    if sat is None:
        return jsonify({"error": "Not found"}), 404
 
    current = sat["stage"]
    if current == STAGES[-1]:
        log("ADVANCE BLOCKED", f"id={sat_id} reason=already_launched")
        return jsonify({"error": f"Already LAUNCHED — final stage, no modifications allowed."}), 400
 
    next_stage = STAGES[STAGE_INDEX[current] + 1]
    sat["stage"] = next_stage
    sat["history"].append({"stage": next_stage, "timestamp": datetime.now().isoformat()})
 
    db = load_db()
    db[sat_id.upper()] = sat
    save_db(db)
    invalidate(sat_id.upper())
    log("ADVANCE", f"id={sat_id} {current} → {next_stage}")
    return jsonify(sat)
 
@app.route("/api/satellites/<sat_id>/skip", methods=["POST"])
def skip_satellite(sat_id):
    """Logic test endpoint — always blocked."""
    sat, _ = get_satellite(sat_id.upper())
    if sat is None:
        return jsonify({"error": "Not found"}), 404
    if sat["stage"] != "Assembled":
        return jsonify({"error": f"Satellite is at '{sat['stage']}', not 'Assembled'"}), 400
    log("ILLEGAL SKIP ATTEMPT", f"id={sat_id} Assembled → Launched BLOCKED")
    return jsonify({"error": "ILLEGAL TRANSITION: Cannot skip from Assembled → Launched. Required: Assembled → Testing → Launched"}), 400
 
@app.route("/api/logs", methods=["GET"])
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return jsonify([l.strip() for l in reversed(lines[-50:])])
 
@app.route("/api/stats", methods=["GET"])
def get_stats():
    db = load_db()
    sats = list(db.values())
    return jsonify({
        "total": len(sats),
        "assembled": sum(1 for s in sats if s["stage"] == "Assembled"),
        "testing":   sum(1 for s in sats if s["stage"] == "Testing"),
        "launched":  sum(1 for s in sats if s["stage"] == "Launched"),
        "cache_size": len(_cache)
    })
 
if __name__ == "__main__":
    log("SYSTEM START", "Orbit Control Web UI launched")
    app.run(debug=True, port=5000)