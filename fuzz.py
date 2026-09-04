#!/usr/bin/env python3
"""Adversarial test suite for the Fly-in parser.

Generates ~200 map files designed to break the parser, runs main.py on each
one, and classifies the result.

    ./fuzz.py                 run everything
    ./fuzz.py -v              also list every ACCEPTED-ODD case
    ./fuzz.py -k connection   only run cases whose name contains "connection"
    PY="python" ./fuzz.py     use a different interpreter

Three expectations are used:

    reject   the subject requires this map to be refused
    accept   the subject requires this map to work
    any      the subject does not say; either outcome is fine, but the
             program must not crash with a traceback

The hard invariant, checked on every single case, is: no traceback, ever.
A parser that refuses something is defensible. A parser that dies with a
stack trace during peer review is not.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

PY = os.environ.get("PY", "uv run python").split()
TIMEOUT = float(os.environ.get("TIMEOUT", "5"))

BASE = """nb_drones: 2
start_hub: start 0 0
hub: a 2 0
end_hub: goal 4 0
connection: start-a
connection: a-goal
"""

CASES: list[tuple[str, str, str]] = []


def case(name: str, content: str, expect: str) -> None:
    """Register one test case."""
    CASES.append((name, content, expect))


def with_nb(value: str) -> str:
    """Base map with a custom nb_drones line."""
    return BASE.replace("nb_drones: 2", f"nb_drones:{value}")


def with_zone(line: str) -> str:
    """Base map with the middle hub line replaced."""
    return BASE.replace("hub: a 2 0", line)


def with_meta(meta: str) -> str:
    """Base map with metadata appended to the middle hub."""
    return BASE.replace("hub: a 2 0", f"hub: a 2 0 {meta}")


def with_conn(line: str) -> str:
    """Base map with the first connection line replaced."""
    return BASE.replace("connection: start-a", line)


def with_conn_meta(meta: str) -> str:
    """Base map with metadata appended to the first connection."""
    return BASE.replace("connection: start-a", f"connection: start-a {meta}")


# ---------------------------------------------------------------------------
# 1. nb_drones
# ---------------------------------------------------------------------------

NB_VALUES = [
    ("plain", " 5", "accept"),
    ("no_space", "5", "accept"),
    ("padded", "     5     ", "accept"),
    ("tab", "\t5", "accept"),
    ("zero", " 0", "reject"),
    ("negative", " -1", "reject"),
    ("negative_big", " -99999", "reject"),
    ("float", " 5.0", "reject"),
    ("float_frac", " 2.5", "reject"),
    ("word", " five", "reject"),
    ("empty", "", "reject"),
    ("spaces_only", "    ", "reject"),
    ("two_numbers", " 2 3", "reject"),
    ("sci_notation", " 1e3", "reject"),
    ("hex", " 0x10", "reject"),
    ("bin", " 0b11", "reject"),
    ("plus_sign", " +3", "any"),
    ("leading_zeros", " 0003", "any"),
    ("underscored", " 1_0", "any"),
    ("unicode_digits", " \u0665", "any"),
    ("nan", " nan", "reject"),
    ("inf", " inf", "reject"),
    ("bool", " True", "reject"),
    ("null_word", " None", "reject"),
    ("comma", " 1,000", "reject"),
    ("huge", " 100000", "any"),
    ("trailing_semicolon", " 3;", "reject"),
    ("quoted", ' "3"', "reject"),
]
for label, value, exp in NB_VALUES:
    case(f"nb_drones/{label}", with_nb(value), exp)

case("nb_drones/missing", BASE.replace("nb_drones: 2\n", ""), "reject")
case("nb_drones/twice_same", "nb_drones: 2\n" + BASE, "any")
case("nb_drones/twice_different", "nb_drones: 7\n" + BASE, "any")
case("nb_drones/declared_last",
     BASE.replace("nb_drones: 2\n", "") + "nb_drones: 2\n", "accept")
case("nb_drones/no_colon", BASE.replace("nb_drones: 2", "nb_drones 2"),
     "reject")
case("nb_drones/double_colon", BASE.replace("nb_drones: 2", "nb_drones:: 2"),
     "reject")
case("nb_drones/uppercase", BASE.replace("nb_drones: 2", "NB_DRONES: 2"),
     "reject")

# ---------------------------------------------------------------------------
# 2. Zone names
# ---------------------------------------------------------------------------

NAME_VALUES = [
    ("simple", "a", "accept"),
    ("underscore", "my_hub", "accept"),
    ("digits", "42", "any"),
    ("leading_digit", "1a", "any"),
    ("dash", "my-hub", "reject"),
    ("dash_leading", "-hub", "reject"),
    ("dash_trailing", "hub-", "reject"),
    ("space_inside", "my hub", "reject"),
    ("unicode", "z\u00f4ne", "any"),
    ("emoji", "\U0001f680", "any"),
    ("very_long", "z" * 300, "any"),
    ("bracket", "z[a]", "any"),
    ("colon", "z:a", "any"),
    ("hash", "z#a", "any"),
    ("quote", 'z"a', "any"),
    ("dot", "z.a", "any"),
    ("slash", "z/a", "any"),
    ("equals", "z=a", "any"),
    ("keyword_hub", "hub", "any"),
    ("keyword_connection", "connection", "any"),
    ("same_as_start", "start", "reject"),
    ("same_as_end", "goal", "reject"),
]
for label, nm, exp in NAME_VALUES:
    body = BASE.replace("hub: a 2 0", f"hub: {nm} 2 0")
    body = body.replace("connection: start-a", f"connection: start-{nm}")
    body = body.replace("connection: a-goal", f"connection: {nm}-goal")
    case(f"name/{label}", body, exp)

case("name/missing", with_zone("hub:  2 0"), "reject")
case("name/only_prefix", with_zone("hub:"), "reject")
case("name/prefix_no_colon", with_zone("hub a 2 0"), "any")
case("name/duplicate", BASE + "hub: a 9 9\n", "reject")
case("name/case_differs", BASE + "hub: A 9 9\n", "any")

# ---------------------------------------------------------------------------
# 3. Coordinates
# ---------------------------------------------------------------------------

COORD_VALUES = [
    ("origin", "0 0", "any"),
    ("negative", "-5 -7", "accept"),
    ("mixed_sign", "-5 7", "accept"),
    ("plus", "+3 +4", "any"),
    ("huge", "999999999999 1", "any"),
    ("float", "1.5 0", "reject"),
    ("float_zero", "1.0 0", "reject"),
    ("sci", "1e2 0", "reject"),
    ("hex", "0x10 0", "reject"),
    ("word", "two 0", "reject"),
    ("empty_y", "2", "reject"),
    ("three_values", "2 0 7", "any"),
    ("tab_separated", "2\t3", "any"),
    ("many_spaces", "2      3", "any"),
    ("unicode_digit", "\u0662 0", "any"),
    ("comma_pair", "2,3", "reject"),
]
for label, coords, exp in COORD_VALUES:
    case(f"coords/{label}", with_zone(f"hub: a {coords}"), exp)

case("coords/duplicate_position", with_zone("hub: a 0 0"), "reject")
case("coords/duplicate_with_end", with_zone("hub: a 4 0"), "reject")

# ---------------------------------------------------------------------------
# 4. Zone metadata
# ---------------------------------------------------------------------------

META_VALUES = [
    ("empty_brackets", "[]", "any"),
    ("only_open", "[", "any"),
    ("only_close", "]", "any"),
    ("unclosed", "[color=red", "any"),
    ("double_close", "[color=red]]", "any"),
    ("double_open", "[[color=red]]", "any"),
    ("nested", "[color=[red]]", "any"),
    ("no_equals", "[color]", "reject"),
    ("double_equals", "[color==red]", "reject"),
    ("equals_only", "[=]", "any"),
    ("empty_key", "[=red]", "any"),
    ("empty_value", "[color=]", "any"),
    ("spaced_equals", "[color = red]", "reject"),
    ("leading_space", "[ color=red ]", "any"),
    ("duplicate_key", "[color=red color=blue]", "any"),
    ("unknown_key", "[speed=3]", "any"),
    ("uppercase_key", "[COLOR=red]", "any"),
    ("uppercase_value", "[zone=NORMAL]", "reject"),
    ("capitalised_value", "[zone=Normal]", "reject"),
    ("trailing_comma", "[color=red,]", "any"),
    ("comma_separated", "[color=red,zone=normal]", "any"),
    ("semicolon_separated", "[color=red;zone=normal]", "any"),
    ("newline_escape", "[color=re\\nd]", "any"),
    ("very_long_value", "[color=" + "r" * 500 + "]", "any"),
]
for label, meta, exp in META_VALUES:
    case(f"meta/{label}", with_meta(meta), exp)

ZONE_TYPES = [
    ("normal", "normal", "accept"),
    ("priority", "priority", "accept"),
    ("restricted", "restricted", "accept"),
    ("blocked_detour_exists", "blocked", "any"),
    ("empty", "", "reject"),
    ("unknown", "teleporter", "reject"),
    ("numeric", "0", "reject"),
    ("plural", "normals", "reject"),
    ("accented", "r\u00e9stricted", "reject"),
    ("spaced", "norm al", "reject"),
    ("bool", "true", "reject"),
]
for label, zt, exp in ZONE_TYPES:
    case(f"zone_type/{label}", with_meta(f"[zone={zt}]"), exp)

CAP_VALUES = [
    ("one", "1", "accept"),
    ("five", "5", "accept"),
    ("zero", "0", "reject"),
    ("negative", "-1", "reject"),
    ("float", "1.5", "reject"),
    ("float_int", "2.0", "reject"),
    ("word", "many", "reject"),
    ("empty", "", "reject"),
    ("plus", "+2", "any"),
    ("leading_zeros", "007", "any"),
    ("sci", "1e2", "reject"),
    ("huge", "999999999", "any"),
    ("bool", "true", "reject"),
    ("infinity", "\u221e", "reject"),
]
for label, cap, exp in CAP_VALUES:
    case(f"max_drones/{label}", with_meta(f"[max_drones={cap}]"), exp)

COLOR_VALUES = [
    ("named", "red", "accept"),
    ("rainbow", "rainbow", "accept"),
    ("hex", "#ff0000", "any"),
    ("unknown", "octarine", "any"),
    ("numeric", "12345", "any"),
    ("empty", "", "any"),
    ("two_words", "light blue", "reject"),
    ("uppercase", "RED", "any"),
    ("very_long", "c" * 400, "any"),
]
for label, col, exp in COLOR_VALUES:
    case(f"color/{label}", with_meta(f"[color={col}]"), exp)

# ---------------------------------------------------------------------------
# 5. Connections
# ---------------------------------------------------------------------------

CONN_VALUES = [
    ("plain", "connection: start-a", "accept"),
    ("no_space", "connection:start-a", "accept"),
    ("padded", "connection:     start-a    ", "accept"),
    ("spaced_dash", "connection: start - a", "any"),
    ("double_dash", "connection: start--a", "reject"),
    ("triple_name", "connection: start-a-goal", "reject"),
    ("missing_left", "connection: -a", "reject"),
    ("missing_right", "connection: start-", "reject"),
    ("no_dash", "connection: start a", "reject"),
    ("empty", "connection:", "reject"),
    ("only_dash", "connection: -", "reject"),
    ("self_loop", "connection: a-a", "any"),
    ("unknown_left", "connection: ghost-a", "reject"),
    ("unknown_right", "connection: start-ghost", "reject"),
    ("both_unknown", "connection: ghost1-ghost2", "reject"),
    ("uppercase_prefix", "CONNECTION: start-a", "reject"),
    ("no_colon", "connection start-a", "any"),
    ("tab_after_colon", "connection:\tstart-a", "accept"),
]
for label, line, exp in CONN_VALUES:
    case(f"connection/{label}", with_conn(line), exp)

case("connection/duplicate_same_order", BASE + "connection: start-a\n",
     "reject")
case("connection/duplicate_reverse", BASE + "connection: a-start\n", "reject")
case("connection/forward_reference",
     "nb_drones: 2\nstart_hub: start 0 0\nconnection: start-a\n"
     "hub: a 2 0\nend_hub: goal 4 0\nconnection: a-goal\n", "reject")
case("connection/none_at_all",
     "nb_drones: 1\nstart_hub: start 0 0\nend_hub: goal 4 0\n", "reject")
case("connection/start_to_end_direct",
     "nb_drones: 3\nstart_hub: start 0 0\nend_hub: goal 1 0\n"
     "connection: start-goal\n", "accept")

CONN_META = [
    ("plain", "[max_link_capacity=2]", "accept"),
    ("zero", "[max_link_capacity=0]", "reject"),
    ("negative", "[max_link_capacity=-2]", "reject"),
    ("float", "[max_link_capacity=1.5]", "reject"),
    ("word", "[max_link_capacity=lots]", "reject"),
    ("empty_value", "[max_link_capacity=]", "reject"),
    ("unknown_key", "[max_speed=3]", "reject"),
    ("zone_key", "[zone=priority]", "reject"),
    ("max_drones_key", "[max_drones=3]", "reject"),
    ("no_equals", "[max_link_capacity]", "reject"),
    ("empty_brackets", "[]", "any"),
    ("unclosed", "[max_link_capacity=2", "any"),
    ("duplicate_key", "[max_link_capacity=2 max_link_capacity=3]", "any"),
    ("huge", "[max_link_capacity=999999999]", "any"),
]
for label, meta, exp in CONN_META:
    case(f"connection_meta/{label}", with_conn_meta(meta), exp)

# ---------------------------------------------------------------------------
# 6. Structure: start and end hubs
# ---------------------------------------------------------------------------

case("structure/no_start", BASE.replace("start_hub: start 0 0",
                                        "hub: start 0 0"), "reject")
case("structure/no_end", BASE.replace("end_hub: goal 4 0",
                                      "hub: goal 4 0"), "reject")
case("structure/two_starts", BASE + "start_hub: start2 9 9\n", "reject")
case("structure/two_ends", BASE + "end_hub: goal2 9 9\n", "reject")
case("structure/three_starts",
     BASE + "start_hub: s2 9 9\nstart_hub: s3 8 8\n", "reject")
case("structure/start_is_end",
     "nb_drones: 1\nstart_hub: start 0 0\nend_hub: start 2 0\n"
     "connection: start-start\n", "reject")
case("structure/end_before_start",
     "nb_drones: 2\nend_hub: goal 4 0\nstart_hub: start 0 0\n"
     "hub: a 2 0\nconnection: start-a\nconnection: a-goal\n", "accept")
case("structure/start_blocked",
     BASE.replace("start_hub: start 0 0",
                  "start_hub: start 0 0 [zone=blocked]"), "any")
case("structure/end_blocked",
     BASE.replace("end_hub: goal 4 0",
                  "end_hub: goal 4 0 [zone=blocked]"), "any")
case("structure/start_restricted",
     BASE.replace("start_hub: start 0 0",
                  "start_hub: start 0 0 [zone=restricted]"), "any")
case("structure/end_restricted",
     BASE.replace("end_hub: goal 4 0",
                  "end_hub: goal 4 0 [zone=restricted]"), "any")
case("structure/start_capacity_ignored",
     "nb_drones: 5\nstart_hub: start 0 0 [max_drones=1]\nhub: a 2 0\n"
     "end_hub: goal 4 0 [max_drones=1]\nconnection: start-a\n"
     "connection: a-goal\n", "accept")
case("structure/isolated_start",
     "nb_drones: 1\nstart_hub: start 0 0\nhub: a 2 0\nend_hub: goal 4 0\n"
     "connection: a-goal\n", "reject")
case("structure/isolated_end",
     "nb_drones: 1\nstart_hub: start 0 0\nhub: a 2 0\nend_hub: goal 4 0\n"
     "connection: start-a\n", "reject")
case("structure/blocked_only_path",
     "nb_drones: 1\nstart_hub: start 0 0\nhub: wall 2 0 [zone=blocked]\n"
     "end_hub: goal 4 0\nconnection: start-wall\nconnection: wall-goal\n",
     "reject")
case("structure/extra_disconnected_island",
     BASE + "hub: island1 20 20\nhub: island2 22 20\n"
     "connection: island1-island2\n", "accept")
case("structure/only_start_and_end_no_link",
     "nb_drones: 1\nstart_hub: start 0 0\nend_hub: goal 4 0\n", "reject")

# ---------------------------------------------------------------------------
# 7. File-level abuse
# ---------------------------------------------------------------------------

case("file/empty", "", "reject")
case("file/whitespace_only", "   \n\t\n  \n", "reject")
case("file/comments_only", "# nothing here\n# still nothing\n", "reject")
case("file/no_trailing_newline", BASE.rstrip("\n"), "accept")
case("file/crlf", BASE.replace("\n", "\r\n"), "any")
case("file/cr_only", BASE.replace("\n", "\r"), "any")
case("file/bom", "\ufeff" + BASE, "any")
case("file/blank_lines_everywhere",
     "\n\n".join(BASE.splitlines()) + "\n", "accept")
case("file/leading_whitespace_lines",
     "".join("   " + ln + "\n" for ln in BASE.splitlines()), "any")
case("file/trailing_whitespace",
     "".join(ln + "    \n" for ln in BASE.splitlines()), "any")
case("file/all_on_one_line", BASE.replace("\n", " "), "reject")
case("file/duplicate_whole_map", BASE + BASE, "reject")
case("file/unknown_prefix", BASE + "airport: JFK 1 1\n", "any")
case("file/garbage_line", BASE + "!!!???\n", "any")
case("file/random_json", BASE + '{"zone": "a"}\n', "any")
case("file/null_byte", BASE + "hub: b\x00 9 9\n", "any")
case("file/control_chars", BASE + "hub: b\x07 9 9\n", "any")
case("file/very_long_line", BASE + "hub: " + "z" * 5000 + " 9 9\n", "any")
case("file/comment_mid_line",
     with_zone("hub: a 2 0 # this is a comment"), "any")
case("file/comment_indented", "  # indented comment\n" + BASE, "any")
case("file/comment_no_space", "#comment\n" + BASE, "accept")
case("file/hash_inside_metadata", with_meta("[color=#red]"), "any")
case("file/only_nb_drones", "nb_drones: 3\n", "reject")
case("file/only_hubs", "start_hub: start 0 0\nend_hub: goal 1 0\n", "reject")

# ---------------------------------------------------------------------------
# 8. Prefix and separator abuse
# ---------------------------------------------------------------------------

PREFIX_CASES = [
    ("hub_uppercase", "HUB: b 9 9", "any"),
    ("hub_mixed_case", "Hub: b 9 9", "any"),
    ("hub_trailing_space", "hub : b 9 9", "any"),
    ("hub_no_space_after_colon", "hub:b 9 9", "any"),
    ("hub_double_colon", "hub:: b 9 9", "any"),
    ("start_hub_typo", "start_hubs: b 9 9", "any"),
    ("end_hub_typo", "endhub: b 9 9", "any"),
    ("hub_with_tab", "hub:\tb\t9\t9", "any"),
]
for label, extra, exp in PREFIX_CASES:
    case(f"prefix/{label}", BASE + extra + "\n", exp)

# ---------------------------------------------------------------------------
# 9. Semantic / routing edge cases
# ---------------------------------------------------------------------------

case("routing/one_drone_direct",
     "nb_drones: 1\nstart_hub: start 0 0\nend_hub: goal 1 0\n"
     "connection: start-goal\n", "accept")
case("routing/bottleneck_capacity_one",
     "nb_drones: 5\nstart_hub: start 0 0\nhub: narrow 2 0\n"
     "end_hub: goal 4 0\nconnection: start-narrow\nconnection: narrow-goal\n",
     "accept")
case("routing/restricted_chain",
     "nb_drones: 2\nstart_hub: start 0 0\nhub: t1 2 0 [zone=restricted]\n"
     "hub: t2 4 0 [zone=restricted]\nend_hub: goal 6 0\n"
     "connection: start-t1\nconnection: t1-t2\nconnection: t2-goal\n",
     "accept")
case("routing/all_priority",
     "nb_drones: 2\nstart_hub: start 0 0\nhub: p1 2 0 [zone=priority]\n"
     "hub: p2 4 0 [zone=priority]\nend_hub: goal 6 0\n"
     "connection: start-p1\nconnection: p1-p2\nconnection: p2-goal\n",
     "accept")
case("routing/dead_end_branch",
     "nb_drones: 2\nstart_hub: start 0 0\nhub: fork 2 0 [max_drones=2]\n"
     "hub: dead 2 4\nhub: live 4 0 [max_drones=2]\nend_hub: goal 6 0\n"
     "connection: start-fork [max_link_capacity=2]\n"
     "connection: fork-dead\n"
     "connection: fork-live [max_link_capacity=2]\n"
     "connection: live-goal [max_link_capacity=2]\n", "accept")
case("routing/long_corridor",
     "nb_drones: 2\n" + "start_hub: h0 0 0\n"
     + "".join(f"hub: h{i} {i} 0\n" for i in range(1, 40))
     + "end_hub: h40 40 0\n"
     + "".join(f"connection: h{i}-h{i + 1}\n" for i in range(40)), "accept")
case("routing/star_topology",
     "nb_drones: 4\nstart_hub: start 0 0\n"
     + "".join(f"hub: arm{i} {i + 1} {i + 1}\n" for i in range(4))
     + "end_hub: goal 20 20\n"
     + "".join(f"connection: start-arm{i}\n" for i in range(4))
     + "".join(f"connection: arm{i}-goal\n" for i in range(4)), "accept")
case("routing/more_drones_than_capacity",
     "nb_drones: 30\nstart_hub: start 0 0\nhub: a 2 0\nend_hub: goal 4 0\n"
     "connection: start-a\nconnection: a-goal\n", "accept")
case("routing/cycle_only",
     "nb_drones: 1\nstart_hub: start 0 0\nhub: a 2 0\nhub: b 4 0\n"
     "end_hub: goal 9 9\nconnection: start-a\nconnection: a-b\n"
     "connection: b-start\n", "reject")
case("routing/all_blocked_middle",
     "nb_drones: 1\nstart_hub: start 0 0\nhub: w1 2 0 [zone=blocked]\n"
     "hub: w2 2 2 [zone=blocked]\nend_hub: goal 4 0\n"
     "connection: start-w1\nconnection: start-w2\nconnection: w1-goal\n"
     "connection: w2-goal\n", "reject")

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_case(path: str) -> tuple[str, int]:
    """Run main.py on *path*, returning (combined output, return code)."""
    env = dict(os.environ)
    env["SDL_VIDEODRIVER"] = "dummy"
    env["PYTHONUNBUFFERED"] = "1"
    try:
        proc = subprocess.run(
            PY + ["main.py", path],
            capture_output=True, text=True, timeout=TIMEOUT, env=env,
        )
        return proc.stdout + proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + (exc.stderr or b"")
        text = out.decode("utf-8", "replace") if isinstance(out, bytes) \
            else str(out)
        return text, 124


def classify(out: str, code: int, expect: str) -> tuple[str, str]:
    """Return (verdict, detail) for one finished run."""
    if "Traceback" in out:
        first = next((ln for ln in out.splitlines()
                      if ln.strip() and not ln.startswith(" ")), "")
        return "CRASH", first[:90]

    ran = code == 124 or (code == 0 and "-goal" in out)
    refused = code != 0 and code != 124

    if expect == "reject":
        if refused:
            return "PASS", ""
        return "FAIL", "accepted an invalid map"
    if expect == "accept":
        if ran:
            return "PASS", ""
        line = next((ln for ln in out.splitlines() if "ERROR" in ln), "")
        return "FAIL", f"refused a valid map: {line[:70]}"
    # expect == "any"
    if ran:
        return "ODD-ACCEPT", ""
    if refused:
        return "OK-REJECT", ""
    return "FAIL", f"unclear outcome (code {code})"


def main() -> int:
    """Generate every case, run it, and print a summary."""
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("-k", "--filter", default="")
    args = ap.parse_args()

    selected = [c for c in CASES if args.filter in c[0]]
    tmp = tempfile.mkdtemp(prefix="flyin_fuzz_")
    counts = {"PASS": 0, "FAIL": 0, "CRASH": 0,
              "ODD-ACCEPT": 0, "OK-REJECT": 0}
    problems: list[tuple[str, str, str]] = []
    odd: list[str] = []

    print(f"running {len(selected)} cases (timeout {TIMEOUT}s)\n")

    for index, (name, content, expect) in enumerate(selected, 1):
        path = os.path.join(tmp, f"{index:03d}.txt")
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        out, code = run_case(path)
        verdict, detail = classify(out, code, expect)
        counts[verdict] += 1
        if verdict in ("FAIL", "CRASH"):
            problems.append((verdict, name, detail))
            print(f"  \033[31m{verdict:10}\033[0m {name} -- {detail}")
        elif verdict == "ODD-ACCEPT":
            odd.append(name)
            if args.verbose:
                print(f"  \033[33m{verdict:10}\033[0m {name}")
        sys.stdout.flush()

    print("\n" + "-" * 60)
    print(f"{counts['PASS']} passed   "
          f"{counts['OK-REJECT']} refused (allowed)   "
          f"{counts['ODD-ACCEPT']} accepted (allowed)")
    print(f"{counts['FAIL']} failed   {counts['CRASH']} crashed")

    if odd and not args.verbose:
        print(f"\n{len(odd)} maps were accepted that the subject does not "
              f"explicitly require accepting.")
        print("Re-run with -v to list them; each one is a question a "
              "reviewer could ask.")

    if problems:
        print("\nproblems:")
        for verdict, name, detail in problems:
            print(f"  {verdict:10} {name} -- {detail}")

    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if counts["FAIL"] or counts["CRASH"] else 0


if __name__ == "__main__":
    sys.exit(main())
