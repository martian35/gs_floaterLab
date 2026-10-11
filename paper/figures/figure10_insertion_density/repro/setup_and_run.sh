#!/usr/bin/env bash
# F10 reproduction on colin. Does not modify colin's code: the patched geometry-ablation harness is copied to a separate
# directory whose siblings are symlinks to colin's live (read-only) mapper_equal_render / mapper_baselines.
#
#   bash setup_and_run.sh prepare            # CPU: source check, repro tree, suite directory
#   bash setup_and_run.sh run                # GPU: 73 runs (~1–1.5 h on an idle RTX 5090-class GPU); ask before running
#   bash setup_and_run.sh summarize          # CPU: tables + comparison with the local 5070 Ti reference
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LIVE=/home/intern/gs_floaterLab/benchmarks/online_gs/campaigns/03_benchmark_contract
REPRO=${F10_REPRO:-/home/intern/gs_floaterLab_figure10_repro/03_benchmark_contract}
OUT=${F10_OUT:-/ssd/intern/paperExperiments/results/campaigns/06_gain_attribution/figure10_utmm_insertion_density/2N_reference_start}
PY="$(python3 -c "import json;print(json.load(open('/home/intern/VIGS-SLAM-custom/scripts/selected_mapping/source_lock.json'))['python_prefix'])")/bin/python"
case "${1:-}" in
  prepare)
    bash "$HERE/check_sources.sh"
    mkdir -p "$REPRO"
    [ -e "$REPRO/mapper_geometry_ablation" ] || cp -r "$HERE/harness/mapper_geometry_ablation" "$REPRO/"
    ln -sfn "$LIVE/mapper_equal_render" "$REPRO/mapper_equal_render"
    ln -sfn "$LIVE/mapper_baselines" "$REPRO/mapper_baselines"
    [ -e "$OUT" ] || python3 "$HERE/make_utmm_suite.py" --output "$OUT"
    echo "repro tree: $REPRO  suite: $OUT  python: $PY" ;;
  run)
    cd /home/intern/VIGS-SLAM-custom
    PYTHONDONTWRITEBYTECODE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    ABLATION_REFERENCE_START=1 ABLATION_ALLOW_NO_DEPTH=1 ABLATION_RPI=2 ABLATION_PLAN="$OUT/plan.json" \
      "$PY" "$REPRO/mapper_geometry_ablation/run_suite_utmm.py" --output "$OUT" > "$OUT/supervisor.log" 2>&1
    echo "exit $?" >> "$OUT/supervisor.log" ;;
  summarize)
    python3 "$HERE/../scripts/summarize_utmm_screen.py" --run-root "$OUT" --out-dir "$OUT/f10_summary" \
      --reference "$HERE/../analysis/utmm_2N_reference_start/runs.csv" ;;
  *) echo "usage: $0 prepare|run|summarize"; exit 2 ;;
esac
