"""
╔══════════════════════════════════════════════════════════════╗
║           O R B I T   C O N T R O L                         ║
║        Satellite Launch Management System v1.0              ║
║                                                             ║
║   Assembled ──────► Testing ──────► Launched                ║
╚══════════════════════════════════════════════════════════════╝
"""
 
import json
import os
import sys
from datetime import datetime
 
# ─── File paths ───────────────────────────────────────────────
DB_FILE  = "satellites_db.json"
LOG_FILE = "log.txt"
 
# ─── Stage definitions ────────────────────────────────────────
STAGES = ["Assembled", "Testing", "Launched"]
STAGE_INDEX = {s: i for i, s in enumerate(STAGES)}
 
# ─── In-memory cache ──────────────────────────────────────────
_cache: dict = {}
 
 
# ══════════════════════════════════════════════════════════════
# LOGGING  (CIA Triad: Confidentiality — every access recorded)
# ══════════════════════════════════════════════════════════════
 
def log(action: str, detail: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {action}"
    if detail:
        line += f" | {detail}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
 
 
# ══════════════════════════════════════════════════════════════
# FILE-BASED PERSISTENCE  (CIA Triad: Availability — crash recovery)
# ══════════════════════════════════════════════════════════════
 
def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
 
 
def save_db(db: dict):
    """Saved immediately after every change — survives any crash."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
 
 
# ══════════════════════════════════════════════════════════════
# CACHE  (Performance improvement)
# ══════════════════════════════════════════════════════════════
 
def get_satellite(sat_id: str) -> dict | None:
    """
    Cache logic:
      1st request → reads from file  (CACHE MISS)
      2nd request → served from dict (CACHE HIT)
    """
    if sat_id in _cache:
        print("  ⚡ [CACHE HIT]  Served from memory — no file I/O needed.")
        log("CACHE HIT", f"id={sat_id}")
        return _cache[sat_id]
 
    db = load_db()
    if sat_id not in db:
        return None
 
    sat = db[sat_id]
    _cache[sat_id] = sat
    print("  💾 [CACHE MISS] Loaded from file database.")
    log("CACHE MISS", f"id={sat_id}")
    return sat
 
 
def invalidate_cache(sat_id: str):
    """Evict stale entry after any mutation."""
    _cache.pop(sat_id, None)
 
 
# ══════════════════════════════════════════════════════════════
# BUSINESS LOGIC  (CIA Triad: Integrity — enforced transitions)
# ══════════════════════════════════════════════════════════════
 
def create_satellite(name: str, mission: str, operator: str) -> dict:
    db = load_db()
    sat_id = f"SAT-{len(db) + 1:04d}"
    ts = datetime.now().isoformat()
    sat = {
        "id":       sat_id,
        "name":     name,
        "mission":  mission,
        "operator": operator,
        "stage":    "Assembled",
        "history":  [{"stage": "Assembled", "timestamp": ts}]
    }
    db[sat_id] = sat
    save_db(db)
    invalidate_cache(sat_id)
    log("CREATE", f"id={sat_id} name={name!r} stage=Assembled")
    return sat
 
 
def advance_stage(sat_id: str) -> tuple[bool, str]:
    sat = get_satellite(sat_id)
    if sat is None:
        return False, f"Satellite '{sat_id}' not found."
 
    current = sat["stage"]
 
    # Final stage lock — cannot modify a launched satellite
    if current == STAGES[-1]:
        log("ADVANCE BLOCKED", f"id={sat_id} reason=already_launched")
        return False, (
            f"🔒 '{sat_id}' is already LAUNCHED. "
            f"Final stage — no modifications allowed."
        )
 
    next_stage = STAGES[STAGE_INDEX[current] + 1]
    sat["stage"] = next_stage
    sat["history"].append({
        "stage":     next_stage,
        "timestamp": datetime.now().isoformat()
    })
 
    # Persist immediately for crash recovery
    db = load_db()
    db[sat_id] = sat
    save_db(db)
    invalidate_cache(sat_id)
    log("ADVANCE", f"id={sat_id} {current} → {next_stage}")
    return True, f"✅ '{sat_id}' advanced: {current} → {next_stage}"
 
 
def attempt_illegal_skip(sat_id: str) -> tuple[bool, str]:
    """Logic test: try to jump Assembled → Launched directly. Must be blocked."""
    sat = get_satellite(sat_id)
    if sat is None:
        return False, f"Satellite '{sat_id}' not found."
 
    if sat["stage"] != "Assembled":
        return False, f"Satellite is at stage '{sat['stage']}', not 'Assembled'."
 
    log("ILLEGAL SKIP ATTEMPT", f"id={sat_id} Assembled → Launched BLOCKED")
    return False, (
        "🚫 ILLEGAL TRANSITION BLOCKED\n"
        "   Cannot skip from 'Assembled' directly to 'Launched'.\n"
        "   Required path: Assembled → Testing → Launched"
    )
 
 
# ══════════════════════════════════════════════════════════════
# SEARCH & FILTER
# ══════════════════════════════════════════════════════════════
 
def search_by_id(sat_id: str) -> dict | None:
    log("SEARCH BY ID", f"id={sat_id}")
    return get_satellite(sat_id)
 
 
def filter_by_stage(stage: str) -> list:
    db = load_db()
    results = [s for s in db.values() if s["stage"].lower() == stage.lower()]
    log("FILTER BY STAGE", f"stage={stage} results={len(results)}")
    return results
 
 
# ══════════════════════════════════════════════════════════════
# DISPLAY HELPERS
# ══════════════════════════════════════════════════════════════
 
STAGE_ICONS = {
    "Assembled": "🔧",
    "Testing":   "🧪",
    "Launched":  "🚀"
}
 
STAGE_BAR = {
    "Assembled": "[■□□] Assembled",
    "Testing":   "[■■□] Testing  ",
    "Launched":  "[■■■] Launched ",
}
 
def print_satellite(s: dict):
    bar = STAGE_BAR.get(s["stage"], s["stage"])
    print(f"""
  ┌──────────────────────────────────────────────┐
  │  ID       : {s['id']:<34}│
  │  Name     : {s['name']:<34}│
  │  Mission  : {s['mission']:<34}│
  │  Operator : {s['operator']:<34}│
  │  Stage    : {bar:<34}│
  └──────────────────────────────────────────────┘
  Stage history:""")
    for h in s["history"]:
        ts = h["timestamp"][:19].replace("T", " ")
        icon = STAGE_ICONS.get(h["stage"], "•")
        print(f"    {icon}  {h['stage']:<12} @ {ts}")
 
 
def print_list(sats: list):
    if not sats:
        print("  (no results)")
        return
    for s in sats:
        icon = STAGE_ICONS.get(s["stage"], "?")
        print(f"  [{s['id']}]  {s['name']:<22} {icon} {s['stage']}")
 
 
def divider():
    print("\n" + "═" * 56)
 
 
# ══════════════════════════════════════════════════════════════
# MENU ACTIONS
# ══════════════════════════════════════════════════════════════
 
def menu_create():
    print("\n  🔧 Register New Satellite")
    name     = input("  Name     : ").strip()
    mission  = input("  Mission  : ").strip()
    operator = input("  Operator : ").strip()
    if not name:
        print("  ❌ Name cannot be empty.")
        return
    s = create_satellite(name, mission, operator)
    print(f"\n  ✅ Satellite registered → ID: {s['id']}")
 
 
def menu_advance():
    print("\n  🧪 Advance Satellite Stage")
    sid = input("  Satellite ID: ").strip().upper()
    ok, msg = advance_stage(sid)
    print(f"\n  {msg}")
 
 
def menu_view():
    print("\n  🔍 View Satellite by ID")
    sid = input("  Satellite ID: ").strip().upper()
    s = search_by_id(sid)
    if s:
        print_satellite(s)
    else:
        print("  ❌ Not found.")
 
 
def menu_filter():
    print("\n  🗂️  Filter by Stage")
    print("  1) Assembled   2) Testing   3) Launched")
    choice = input("  Choose (1/2/3): ").strip()
    stage_map = {"1": "Assembled", "2": "Testing", "3": "Launched"}
    stage = stage_map.get(choice)
    if not stage:
        print("  ❌ Invalid choice.")
        return
    results = filter_by_stage(stage)
    print(f"\n  Satellites in '{stage}':")
    print_list(results)
 
 
def menu_list_all():
    print("\n  📜 All Satellites")
    db = load_db()
    log("LIST ALL", f"count={len(db)}")
    print_list(list(db.values()))
 
 
def menu_cache_demo():
    print("\n  ⚡ Cache Demo — watch MISS then HIT")
    sid = input("  Satellite ID: ").strip().upper()
 
    # Evict from cache first — guarantees Request 1 is always a MISS
    invalidate_cache(sid)
    print("  (cache cleared — clean demo guaranteed)\n")
 
    print("  ── Request 1 ──────────────────────────")
    s = get_satellite(sid)
    if s: print(f"  Result: {s['name']}")
    print("\n  ── Request 2 ──────────────────────────")
    s = get_satellite(sid)
    if s: print(f"  Result: {s['name']}")
 
 
def menu_logic_test():
    print("\n  🧪 Logic Test — Illegal Stage Skip")
    sid = input("  Satellite ID (must be 'Assembled'): ").strip().upper()
    ok, msg = attempt_illegal_skip(sid)
    print(f"\n  {msg}")
 
 
# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
 
BANNER = r"""
   ___  ____  ____ ___ _____    ____  ___  _   _ _____ ____   ___  _
  / _ \|  _ \| __ )_ _|_   _|  / ___|/ _ \| \ | |_   _|  _ \ / _ \| |
 | | | | |_) |  _ \| |  | |   | |   | | | |  \| | | | | |_) | | | | |
 | |_| |  _ <| |_) | |  | |   | |___| |_| | |\  | | | |  _ <| |_| | |___
  \___/|_| \_\____/___| |_|    \____|\___/|_| \_| |_| |_| \_\\___/|_____|
 
         Satellite Launch Management System  ·  Mission Control
         Assembled ──────────► Testing ──────────► Launched
"""
 
MENU = """
  [1]  Register new satellite        (Create)
  [2]  Advance to next stage         (Update)
  [3]  View satellite by ID          (Search)
  [4]  Filter satellites by stage    (Filter)
  [5]  List all satellites
  ─────────────────────────────────────────────
  [6]  Cache demo   (MISS → HIT)
  [7]  Logic test   (illegal skip → blocked)
  ─────────────────────────────────────────────
  [0]  Exit
"""
 
def main():
    print(BANNER)
    log("SYSTEM START", "Orbit Control launched")
 
    while True:
        divider()
        print(MENU)
        choice = input("  Mission Control > ").strip()
 
        if   choice == "1": menu_create()
        elif choice == "2": menu_advance()
        elif choice == "3": menu_view()
        elif choice == "4": menu_filter()
        elif choice == "5": menu_list_all()
        elif choice == "6": menu_cache_demo()
        elif choice == "7": menu_logic_test()
        elif choice == "0":
            log("SYSTEM STOP", "Operator exited")
            print("\n  🌌 Mission Control signing off...\n")
            sys.exit(0)
        else:
            print("  ❓ Unknown command. Try again.")
 
 
if __name__ == "__main__":
    main()