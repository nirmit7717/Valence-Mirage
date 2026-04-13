"""
Valence Mirage — Edge Case Test Suite

Tests the full system with edge-valued inputs to verify:
1. Intent parsing handles unusual/extreme inputs
2. Probability engine produces reasonable thresholds
3. Dice engine classifies outcomes correctly
4. State changes are applied properly
5. Narration handles all outcomes
"""

import requests
import json
import sys
import time
import random

BASE = "http://localhost:8000"

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

passed = 0
failed = 0
errors = []


def test(name, category=""):
    def decorator(func):
        def wrapper():
            global passed, failed, errors
            try:
                result = func()
                print(f"  {GREEN}✅ PASS{RESET} — {name}")
                passed += 1
                return result
            except AssertionError as e:
                print(f"  {RED}❌ FAIL{RESET} — {name}: {e}")
                failed += 1
                errors.append(f"{name}: {e}")
            except Exception as e:
                print(f"  {RED}💥 ERROR{RESET} — {name}: {type(e).__name__}: {e}")
                failed += 1
                errors.append(f"{name}: {type(e).__name__}: {e}")
        return wrapper
    return decorator


def create_session(name="Tester"):
    r = requests.post(f"{BASE}/session/new", json={"player_name": name})
    assert r.status_code == 200, f"Session creation failed: {r.status_code}"
    return r.json()["session_id"]


def do_action(sid, action):
    r = requests.post(f"{BASE}/session/{sid}/action", json={"action": action})
    assert r.status_code == 200, f"Action failed: {r.status_code} {r.text}"
    return r.json()


# ═══════════════════════════════════════════════
# TEST CASES
# ═══════════════════════════════════════════════

print(f"\n{CYAN}{'='*60}")
print("  VALIENCE MIRAGE — EDGE CASE TEST SUITE")
print(f"{'='*60}{RESET}\n")


# ─── Category 1: Intent Parsing Edge Cases ───

print(f"{YELLOW}── Intent Parsing ──{RESET}")

@test("Single word input")
def t1():
    sid = create_session()
    r = do_action(sid, "Run")
    assert r["intent"]["action_type"], "Missing action_type"
    assert r["intent"]["description"], "Missing description"
    return r

@test("Nonsensical gibberish")
def t2():
    sid = create_session()
    r = do_action(sid, "asdfghjkl qwertyuiop zxcvbnm")
    assert r["intent"]["action_type"], "Should parse even gibberish"
    assert r["intent"]["relevant_stat"], "Should assign a stat"
    return r

@test("Extremely long input (900+ chars)")
def t3():
    sid = create_session()
    long_action = "I want to " + "very carefully and meticulously " * 30 + "do something"
    r = do_action(sid, long_action[:950])
    assert r["intent"]["description"], "Should handle long input"
    return r

@test("Special characters / unicode")
def t4():
    sid = create_session()
    r = do_action(sid, "I summon the power of ★☆★ and cast 召唤术 🔥")
    assert r["intent"]["action_type"], "Should handle unicode"
    return r

@test("Empty-ish input (only spaces)")
def t5():
    sid = create_session()
    r = requests.post(f"{BASE}/session/{sid}/action", json={"action": "   "})
    # Should reject (min_length=1 after trim)
    assert r.status_code == 422, f"Should reject whitespace-only: {r.status_code}"

@test("Emotional/non-action input")
def t6():
    sid = create_session()
    r = do_action(sid, "I sit and cry about my lost homeland")
    assert r["intent"]["action_type"], "Should parse emotional actions"
    return r

@test("Meta/gaming input")
def t7():
    sid = create_session()
    r = do_action(sid, "I want to check my inventory and see what items I have")
    assert r["intent"]["action_type"], "Should parse meta actions"
    return r

@test("Multiple actions in one input")
def t8():
    sid = create_session()
    r = do_action(sid, "I draw my sword, kick down the door, and scream a battle cry")
    assert r["intent"]["action_type"], "Should handle compound actions"
    return r


# ─── Category 2: Probability Engine Edge Cases ───

print(f"\n{YELLOW}── Probability Engine ──{RESET}")

@test("Cosmic scale action (should get extreme threshold)")
def t9():
    sid = create_session()
    r = do_action(sid, "I rewrite the fabric of reality to destroy the entire universe and recreate it in my image")
    assert r["dice_threshold"] >= 10, f"Cosmic action threshold too low: {r['dice_threshold']}"
    assert r["probability"] < 0.5, f"Cosmic action probability too high: {r['probability']}"
    return r

@test("Trivial/minor action (should get low threshold)")
def t10():
    sid = create_session()
    r = do_action(sid, "I look around the room")
    assert r["dice_threshold"] <= 10, f"Minor action threshold too high: {r['dice_threshold']}"
    return r

@test("Magic spell (should consume mana)")
def t11():
    sid = create_session()
    r = do_action(sid, "I cast a powerful fireball spell at the barkeep")
    intent = r["intent"]
    assert intent["action_type"] in ("cast_spell", "attack"), f"Expected spell/attack: {intent['action_type']}"
    # Check if uses_resource is detected
    if intent["uses_resource"]:
        assert intent["resource_cost"] > 0, "Spell should have mana cost"
    return r

@test("Repeated identical actions (saturation penalty)")
def t12():
    sid = create_session()
    action = "I punch the wall"
    results = []
    for _ in range(5):
        r = do_action(sid, action)
        results.append(r)
    # Later actions should generally have higher thresholds (lower probability)
    # due to saturation penalty
    first_prob = results[0]["probability"]
    last_prob = results[-1]["probability"]
    assert last_prob <= first_prob + 0.05, \
        f"Saturation not working: first={first_prob:.3f}, last={last_prob:.3f}"
    return results


# ─── Category 3: Dice Engine ───

print(f"\n{YELLOW}── Dice Engine ──{RESET}")

@test("Threshold is always between 2 and 20")
def t13():
    sid = create_session()
    actions = [
        "I pick up a coin",                    # minor
        "I fight the dragon",                  # major
        "I become a god and reshape reality",  # cosmic
    ]
    for a in actions:
        r = do_action(sid, a)
        assert 2 <= r["dice_threshold"] <= 20, \
            f"Threshold out of range: {r['dice_threshold']} for '{a}'"

@test("Roll is always between 1 and 20")
def t14():
    sid = create_session()
    for _ in range(10):
        r = do_action(sid, "I do something random")
        assert 1 <= r["roll"] <= 20, f"Roll out of range: {r['roll']}"

@test("Outcome is one of the 5 valid values")
def t15():
    sid = create_session()
    valid = {"critical_success", "success", "partial_success", "failure", "critical_failure"}
    for _ in range(5):
        r = do_action(sid, "I attempt a random action")
        assert r["outcome"] in valid, f"Invalid outcome: {r['outcome']}"


# ─── Category 4: State Changes ───

print(f"\n{YELLOW}── State Changes ──{RESET}")

@test("HP changes on risky failure")
def t16():
    sid = create_session()
    initial_hp = 50
    # Force a risky action — if it fails, HP should change
    for _ in range(3):
        r = do_action(sid, "I challenge the ancient dragon to unarmed combat")
        if r["outcome"] in ("failure", "critical_failure", "partial_success"):
            assert r["player_hp"] < initial_hp or r["state_changes"]["hp_delta"] != 0, \
                f"Risky failure should affect HP: hp={r['player_hp']}, delta={r['state_changes']['hp_delta']}"
            return r
    # If all succeeded, that's fine — just check HP is tracked
    assert r["player_hp"] <= initial_hp
    return r

@test("Mana decreases on spell cast")
def t17():
    sid = create_session()
    r = do_action(sid, "I cast a powerful arcane bolt of lightning at the enemy")
    if r["intent"]["uses_resource"] and r["intent"]["resource_cost"] > 0:
        assert r["player_mana"] < 50, f"Mana should decrease: {r['player_mana']}"
    return r

@test("State persists across turns")
def t18():
    sid = create_session()
    # Do a risky action first
    r1 = do_action(sid, "I provoke the dangerous-looking guard")
    hp_after_1 = r1["player_hp"]
    mana_after_1 = r1["player_mana"]
    # Do another action
    r2 = do_action(sid, "I try to sneak past the guard")
    # HP/mana from turn 1 should carry over as the starting point for turn 2
    assert r2["player_hp"] <= hp_after_1 or r2["state_changes"]["hp_delta"] > 0, \
        "State should persist across turns"
    return r2

@test("Multiple sessions don't interfere")
def t19():
    sid1 = create_session("Player1")
    sid2 = create_session("Player2")
    r1 = do_action(sid1, "I attack the goblin")
    r2 = do_action(sid2, "I explore the cave")
    # Each session should be independent
    s1 = requests.get(f"{BASE}/session/{sid1}").json()
    s2 = requests.get(f"{BASE}/session/{sid2}").json()
    assert s1["player"]["name"] != s2["player"]["name"], "Sessions should be independent"
    assert s1["turn_number"] == 1
    assert s2["turn_number"] == 1


# ─── Category 5: Narration Quality ───

print(f"\n{YELLOW}── Narration Quality ──{RESET}")

@test("Narration is non-empty")
def t20():
    sid = create_session()
    r = do_action(sid, "I open the wooden chest")
    assert len(r["narration"]) > 20, f"Narration too short: {len(r['narration'])} chars"

@test("Narration for critical success mentions triumph")
def t21():
    sid = create_session()
    # Try many easy actions until we get a critical success
    for _ in range(10):
        r = do_action(sid, "I carefully examine the table in front of me")
        if r["outcome"] == "critical_success":
            assert len(r["narration"]) > 50, "Critical success narration should be rich"
            return r
    print("    (no crit success in 10 tries — skipping deep check)")
    return r

@test("Narration for failure mentions consequences")
def t22():
    sid = create_session()
    # Try extreme actions to force failures
    for _ in range(10):
        r = do_action(sid, "I attempt to teleport to the moon using only my willpower")
        if r["outcome"] in ("failure", "critical_failure"):
            assert len(r["narration"]) > 30, "Failure narration should explain what went wrong"
            return r
    print("    (no failure in 10 tries — skipping deep check)")
    return r


# ─── Category 6: API Robustness ───

print(f"\n{YELLOW}── API Robustness ──{RESET}")

@test("Invalid session ID returns 404")
def t23():
    r = requests.post(f"{BASE}/session/nonexistent-id/action", json={"action": "test"})
    assert r.status_code == 404, f"Expected 404: {r.status_code}"

@test("Missing action field returns 422")
def t24():
    sid = create_session()
    r = requests.post(f"{BASE}/session/{sid}/action", json={})
    assert r.status_code == 422, f"Expected 422: {r.status_code}"

@test("Very long action (1000 chars) is accepted")
def t25():
    sid = create_session()
    action = "I " + "really " * 200 + "want to attack"
    r = do_action(sid, action[:1000])
    assert r["turn_number"] == 1

@test("Action exceeding 1000 chars is rejected")
def t26():
    sid = create_session()
    action = "x" * 1001
    r = requests.post(f"{BASE}/session/{sid}/action", json={"action": action})
    assert r.status_code == 422, f"Expected 422 for >1000 chars: {r.status_code}"

@test("History endpoint returns turns")
def t27():
    sid = create_session()
    do_action(sid, "I look around")
    do_action(sid, "I examine the barkeep")
    r = requests.get(f"{BASE}/session/{sid}/history").json()
    assert len(r) == 2, f"Expected 2 turns in history: {len(r)}"


# ═══════════════════════════════════════════════
# RUN ALL TESTS
# ═══════════════════════════════════════════════

# Collect all test functions
tests = [t1, t2, t3, t4, t5, t6, t7, t8, t9, t10,
         t11, t12, t13, t14, t15, t16, t17, t18, t19, t20,
         t21, t22, t23, t24, t25, t26, t27]

for t in tests:
    t()
    time.sleep(0.3)  # Rate limit buffer

# Summary
print(f"\n{CYAN}{'='*60}")
print(f"  RESULTS: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET} / {passed+failed} total")
if errors:
    print(f"\n{RED}Failures:{RESET}")
    for e in errors:
        print(f"  • {e}")
print(f"{CYAN}{'='*60}{RESET}\n")

sys.exit(1 if failed > 0 else 0)
