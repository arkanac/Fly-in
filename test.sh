#!/usr/bin/env bash
# Fly-in test harness.
# Generates a set of maps under tests/maps/ then runs main.py on each one.
#
#   ./test.sh              run everything
#   PY="python" ./test.sh  use a different interpreter
#   TIMEOUT=8 ./test.sh    give the simulation more time before killing it
#
# Valid maps: the program must print a simulation and never crash.
# Invalid maps: the program must exit 1 with a clean "ERROR:" line, no traceback.

set -u

PY=${PY:-"uv run python"}
TIMEOUT=${TIMEOUT:-5}
DIR=tests/maps

export SDL_VIDEODRIVER=dummy   # no pygame window
export PYTHONUNBUFFERED=1      # keep stdout when the timeout kills us

pass=0
fail=0
failed_names=()

mkdir -p "$DIR/valid" "$DIR/invalid"

# --------------------------------------------------------------------------
# Valid maps
# --------------------------------------------------------------------------

cat > "$DIR/valid/01_linear.txt" << 'EOF'
nb_drones: 2
start_hub: start 0 0 [color=green]
hub: waypoint1 2 0
hub: waypoint2 4 0
end_hub: goal 6 0 [color=yellow]
connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
EOF

cat > "$DIR/valid/02_fork.txt" << 'EOF'
nb_drones: 4
start_hub: start 0 0
hub: north1 2 2
hub: north2 4 2
hub: south1 2 -2
hub: south2 4 -2
end_hub: goal 6 0
connection: start-north1
connection: north1-north2
connection: north2-goal
connection: start-south1
connection: south1-south2
connection: south2-goal
EOF

cat > "$DIR/valid/03_restricted.txt" << 'EOF'
nb_drones: 3
start_hub: start 0 0
hub: tunnel 2 0 [zone=restricted color=red max_drones=2]
hub: mid 4 0 [max_drones=2]
end_hub: goal 6 0
connection: start-tunnel [max_link_capacity=2]
connection: tunnel-mid [max_link_capacity=2]
connection: mid-goal [max_link_capacity=2]
EOF

cat > "$DIR/valid/04_priority.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: plain 2 2
hub: fast 2 -2 [zone=priority color=green]
end_hub: goal 4 0
connection: start-plain
connection: plain-goal
connection: start-fast
connection: fast-goal
EOF

cat > "$DIR/valid/05_blocked_detour.txt" << 'EOF'
nb_drones: 2
start_hub: start 0 0
hub: wall 2 0 [zone=blocked color=gray]
hub: detour1 2 3
hub: detour2 4 3
end_hub: goal 6 0
connection: start-wall
connection: wall-goal
connection: start-detour1
connection: detour1-detour2
connection: detour2-goal
EOF

cat > "$DIR/valid/06_zone_capacity.txt" << 'EOF'
nb_drones: 3
start_hub: start 0 0
hub: narrow 2 0
end_hub: goal 4 0
connection: start-narrow
connection: narrow-goal
EOF

cat > "$DIR/valid/07_link_capacity.txt" << 'EOF'
nb_drones: 3
start_hub: start 0 0
hub: wide 2 0 [max_drones=3]
end_hub: goal 4 0
connection: start-wide [max_link_capacity=1]
connection: wide-goal [max_link_capacity=3]
EOF

cat > "$DIR/valid/08_syntax_corner.txt" << 'EOF'
# comment on the first line

nb_drones: 2
start_hub: start 0 0 [max_drones=1 color=rainbow]

# metadata given in both orders, capacity on start/end must be ignored
hub: a 2 0 [color=blue zone=normal]
hub: b 4 0 [zone=normal color=blue]
end_hub: goal 6 0 [max_drones=1]

connection: start-a
connection: a-b
connection: b-goal
EOF

cat > "$DIR/valid/09_single_drone.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
end_hub: goal 1 0
connection: start-goal
EOF

cat > "$DIR/valid/10_many_drones.txt" << 'EOF'
nb_drones: 20
start_hub: start 0 0
hub: hub1 2 2 [max_drones=5]
hub: hub2 2 -2 [max_drones=5]
end_hub: goal 4 0
connection: start-hub1 [max_link_capacity=5]
connection: start-hub2 [max_link_capacity=5]
connection: hub1-goal [max_link_capacity=5]
connection: hub2-goal [max_link_capacity=5]
EOF

cat > "$DIR/valid/11_negative_coords.txt" << 'EOF'
nb_drones: 2
start_hub: start -5 -5
hub: mid -2 -8 [max_drones=2]
end_hub: goal 0 -12
connection: start-mid [max_link_capacity=2]
connection: mid-goal [max_link_capacity=2]
EOF

# --------------------------------------------------------------------------
# Invalid maps
# --------------------------------------------------------------------------

cat > "$DIR/invalid/01_no_start.txt" << 'EOF'
nb_drones: 1
hub: a 0 0
end_hub: goal 2 0
connection: a-goal
EOF

cat > "$DIR/invalid/02_two_starts.txt" << 'EOF'
nb_drones: 1
start_hub: start1 0 0
start_hub: start2 1 0
end_hub: goal 2 0
connection: start1-goal
EOF

cat > "$DIR/invalid/03_no_end.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0
connection: start-a
EOF

cat > "$DIR/invalid/04_two_ends.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
end_hub: goal1 2 0
end_hub: goal2 3 0
connection: start-goal1
EOF

cat > "$DIR/invalid/05_duplicate_zone.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0
hub: a 3 0
end_hub: goal 4 0
connection: start-a
connection: a-goal
EOF

cat > "$DIR/invalid/06_duplicate_coords.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0
hub: b 2 0
end_hub: goal 4 0
connection: start-a
connection: a-goal
EOF

cat > "$DIR/invalid/07_dash_in_name.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: my-hub 2 0
end_hub: goal 4 0
connection: start-goal
EOF

cat > "$DIR/invalid/08_bad_zone_type.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0 [zone=teleporter]
end_hub: goal 4 0
connection: start-a
connection: a-goal
EOF

cat > "$DIR/invalid/09_zero_max_drones.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0 [max_drones=0]
end_hub: goal 4 0
connection: start-a
connection: a-goal
EOF

cat > "$DIR/invalid/10_zero_link_capacity.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0
end_hub: goal 4 0
connection: start-a [max_link_capacity=0]
connection: a-goal
EOF

cat > "$DIR/invalid/11_unknown_hub.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
end_hub: goal 4 0
connection: start-ghost
EOF

cat > "$DIR/invalid/12_forward_reference.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
connection: start-a
hub: a 2 0
end_hub: goal 4 0
connection: a-goal
EOF

cat > "$DIR/invalid/13_duplicate_connection.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0
end_hub: goal 4 0
connection: start-a
connection: a-start
connection: a-goal
EOF

cat > "$DIR/invalid/14_nb_drones_zero.txt" << 'EOF'
nb_drones: 0
start_hub: start 0 0
end_hub: goal 2 0
connection: start-goal
EOF

cat > "$DIR/invalid/15_nb_drones_negative.txt" << 'EOF'
nb_drones: -3
start_hub: start 0 0
end_hub: goal 2 0
connection: start-goal
EOF

cat > "$DIR/invalid/16_nb_drones_nan.txt" << 'EOF'
nb_drones: five
start_hub: start 0 0
end_hub: goal 2 0
connection: start-goal
EOF

cat > "$DIR/invalid/17_bad_metadata.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0 [color]
end_hub: goal 4 0
connection: start-a
connection: a-goal
EOF

cat > "$DIR/invalid/18_color_with_space.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0 [color=light blue]
end_hub: goal 4 0
connection: start-a
connection: a-goal
EOF

cat > "$DIR/invalid/19_unknown_conn_key.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0
end_hub: goal 4 0
connection: start-a [max_speed=3]
connection: a-goal
EOF

cat > "$DIR/invalid/20_malformed_connection.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a 2 0
end_hub: goal 4 0
connection: start-a-goal
EOF

cat > "$DIR/invalid/21_bad_coords.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: a two 0
end_hub: goal 4 0
connection: start-a
connection: a-goal
EOF

cat > "$DIR/invalid/22_unreachable_end.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: island 5 5
end_hub: goal 9 9
connection: start-island
EOF

cat > "$DIR/invalid/23_blocked_only_path.txt" << 'EOF'
nb_drones: 1
start_hub: start 0 0
hub: wall 2 0 [zone=blocked]
end_hub: goal 4 0
connection: start-wall
connection: wall-goal
EOF

cat > "$DIR/invalid/24_empty_file.txt" << 'EOF'
# nothing but a comment
EOF

# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

ok()  { pass=$((pass + 1)); printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
ko()  { fail=$((fail + 1)); failed_names+=("$1")
        printf '  \033[31mFAIL\033[0m  %s -- %s\n' "$1" "$2"; }

run_map() {   # run_map <path> -> sets $out and $code
    out=$(timeout "$TIMEOUT" $PY main.py "$1" 2>&1)
    code=$?
}

check_valid() {
    local map=$1 name
    name=$(basename "$map")
    run_map "$map"

    # 124 = killed by timeout, which is expected: the pygame loop never ends
    if [ "$code" -ne 0 ] && [ "$code" -ne 124 ]; then
        ko "$name" "exit code $code"; return
    fi
    if grep -q "Traceback" <<< "$out"; then
        ko "$name" "uncaught exception"; return
    fi
    if grep -q "^ERROR:" <<< "$out"; then
        ko "$name" "refused a valid map: $(grep -m1 '^ERROR:' <<< "$out")"
        return
    fi
    if ! grep -qE "^D1-" <<< "$out"; then
        ko "$name" "no simulation output"; return
    fi
    ok "$name"
}

check_invalid() {
    local map=$1 name
    name=$(basename "$map")
    run_map "$map"

    if grep -q "Traceback" <<< "$out"; then
        ko "$name" "crashed instead of reporting an error"; return
    fi
    if [ "$code" -eq 124 ]; then
        ko "$name" "accepted an invalid map (ran the simulation)"; return
    fi
    if [ "$code" -eq 0 ]; then
        ko "$name" "exit code 0 on an invalid map"; return
    fi
    if ! grep -q "ERROR" <<< "$out"; then
        ko "$name" "no error message"; return
    fi
    ok "$name"
}

echo
echo "== valid maps =============================================="
for m in "$DIR"/valid/*.txt; do check_valid "$m"; done

echo
echo "== invalid maps ==========================================="
for m in "$DIR"/invalid/*.txt; do check_invalid "$m"; done

# --------------------------------------------------------------------------
# Behaviour checks on the output itself
# --------------------------------------------------------------------------

echo
echo "== behaviour =============================================="

# a drone must never appear twice on the same turn line
run_map "$DIR/valid/02_fork.txt"
dupes=$(grep "^D" <<< "$out" | tr ' ' '\n' | sed 's/-.*//' \
        | awk 'NF' | sort | uniq -d | head -1)
line_dupes=$(grep "^D" <<< "$out" | while read -r line; do
    echo "$line" | tr ' ' '\n' | sed 's/-.*//' | sort | uniq -d
done | head -1)
if [ -n "$line_dupes" ]; then
    ko "no duplicate drone per turn" "$line_dupes appears twice on one line"
else
    ok "no duplicate drone per turn"
fi

# a blocked zone must never be entered
run_map "$DIR/valid/05_blocked_detour.txt"
if grep -q -- "-wall" <<< "$out"; then
    ko "blocked zone avoided" "a drone entered 'wall'"
else
    ok "blocked zone avoided"
fi

# on two equal-length routes the priority one wins
run_map "$DIR/valid/04_priority.txt"
if grep -q -- "-fast" <<< "$out"; then
    ok "priority zone preferred"
else
    ko "priority zone preferred" "took the plain route"
fi

# entering a restricted zone shows a transit step
run_map "$DIR/valid/03_restricted.txt"
if grep -qE "D[0-9]+-[a-z_]+-[a-z_]+" <<< "$out"; then
    ok "restricted transit displayed"
else
    ko "restricted transit displayed" "no D<id>-<a>-<b> line"
fi

# every drone must reach the end zone
run_map "$DIR/valid/10_many_drones.txt"
arrived=$(grep -o "D[0-9]*-goal" <<< "$out" | sort -u | wc -l)
if [ "$arrived" -eq 20 ]; then
    ok "all 20 drones delivered"
else
    ko "all 20 drones delivered" "only $arrived reached the goal"
fi

# --------------------------------------------------------------------------
# Lint
# --------------------------------------------------------------------------

echo
echo "== lint ==================================================="
if make lint > /tmp/flyin_lint.log 2>&1; then
    ok "make lint"
else
    ko "make lint" "see /tmp/flyin_lint.log"
fi

# --------------------------------------------------------------------------

echo
echo "-----------------------------------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
if [ "$fail" -gt 0 ]; then
    printf 'failed: %s\n' "${failed_names[*]}"
    exit 1
fi