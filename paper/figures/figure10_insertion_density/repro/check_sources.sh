#!/usr/bin/env bash
# Read-only check that colin's live code is the state the F10 runs used (2026-10-09 snapshot). Exit 0 = match.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LIVE=/home/intern/gs_floaterLab/benchmarks/online_gs/campaigns/03_benchmark_contract
rc=0
(cd "$LIVE" && sha256sum -c --quiet "$HERE/colin_siblings.sha256") || { echo "mapper_equal_render / mapper_baselines differ"; rc=1; }
(cd "$LIVE/mapper_geometry_ablation" && sha256sum -c --quiet "$HERE/colin_original_ablation.sha256") \
  || echo "note: colin's own mapper_geometry_ablation changed since 2026-10-09 (F10 does not use it; overlay is self-contained)"
cd /home/intern/VIGS-SLAM-custom
[ "$(git rev-parse HEAD)" = 4ad394967899e13d9082d3625d991598ac859f1c ] || { echo "VIGS-SLAM-custom HEAD differs"; rc=1; }
[ "$(git diff | sha256sum | cut -c1-64)" = "$(cat "$HERE/vigs_custom_diff.sha256")" ] || { echo "VIGS-SLAM-custom uncommitted diff differs"; rc=1; }
[ $rc = 0 ] && echo "sources match the F10 run state"
exit $rc
