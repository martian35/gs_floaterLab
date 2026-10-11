# D full replay with FIFO GPU / RAM / SSD image storage

2026-10-11. User authorized §3.2.4 implementation and D storage-only changes,
with both held-out quality and elapsed-time validation. **Completed: 17 training,
held-out evaluation and contract/storage audits (12 controlled storage runs, two
historical-D runs, two native-frontend runs and one forced-SSD run).**

## Contract

- Retain all admitted KF+dense observations. Physical image eviction is independent
  of ERVS membership and counts. κ=16, temporal-gap admission, 3:3:6 view groups,
  distinct images per group and one optimizer step per image remain unchanged.
- One FIFO ordered by arrival, independent of KF/dense role: 512 GPU / 1,024 RAM
  image bundles, then SSD-backed files. Reads do not promote old images. Original
  uint8 and exact normalized float32 pixels are stored losslessly. One CPU bundle
  and one GPU image may be held as scratch; construction temporaries are excluded.
- Frontend image/depth/normal buffers, mapper geometric targets, masks and Gaussian
  storage remain separate. This does not bound whole-system VRAM/RAM or disk usage.
- `full_ram` retains full logical membership with historical RAM/cached-dense and
  resident-KF behavior; `tiered_fifo` changes storage only relative to that control.
  `legacy` also retains historical candidate expiry and dense pool replacement.
  That arm isolates the effect of removing old logical retention limits separately.
- Common causal frontend tapes, identical reference poses, frontend-estimated depth,
  disjoint held-out views, full-input 6N. This is the established mapping-only
  reference-pose benchmark, not strict sensor-only SLAM or a real-time claim.
- Two executions per storage/scene, seed0 in both (runtime repeatability, not two
  independent algorithm seeds), reversed arm order on repeat two. Native frontend
  + mapper and historical D checks are separate arms.
- Jupyter PID1842652 coexists under the user's existing authorization; no unrelated
  process is terminated.

## Completed SSD stress check

RPNG table_01, GPU16 / RAM32, 11,736 image-wise optimizer steps. Held-out PSNR
22.424847, SSIM0.716027, LPIPS0.211994. Mapper 125.177829s, whole 145.628707s.
1,956 arrived images remain logically accessible, 1,908 at the SSD tier. 6,151
camera adoptions validated exact original pixels. Full work/causality/evaluation
and storage audit passed. CPU unit checks cover zero-capacity tiers, lossless
roundtrip, duplicate rejection and no promotion on old-image reads.

SSD counters: 1,908 writes (6.068GB), 14,650 reads (46.591GB); read host wall8.168s,
write wall2.663s. These are buffered filesystem reads/writes: OS page cache is
enabled, so these are **not physical disk-bus measurements**. H2D logical traffic
35.086GB / host3.768s includes admission and export, not only training iterations.
This stress run tests small-capacity operation; its timing is not the default
512/1024 configuration's timing.

## Shared-frontend results (12/12 completed)

Full logical retention in both arms; two executions per arm, fixed seed0.

| Scene | RAM PSNR | FIFO PSNR | Δ PSNR | RAM mapper s | FIFO mapper s | Time change |
|---|---:|---:|---:|---:|---:|---:|
| aria | 25.651497 | 25.635597 | -0.015900 | 74.538 | 78.849 | +5.78% |
| rpng | 22.420478 | 22.423571 | +0.003093 | 108.400 | 114.247 | +5.39% |
| tum_rgbd | 19.959462 | 19.945485 | -0.013977 | 19.633 | 20.074 | +2.25% |

All six pairs have identical view selection sequences, membership/admission/count
histories, causal camera poses and completed optimizer steps. All 12 independent
work/held-out/source/storage audits pass. Final map files are not bit-identical;
small numerical quality differences remain. These same-seed repetitions do not
establish statistical quality equivalence or generalization across seeds.

The default storage change adds 2.25–5.78% mapper time in these runs; there is no
observed speedup. Default VRAM usage can increase on short scenes because the new
512-image GPU tier is larger than the former resident-KF/dense-cache footprint.
The guarantee concerns a configured RGB residency cap as the stream grows, not
a lower total process memory peak in every scene.

Forced SSD stress versus RPNG full_ram r0: same image sequence/admissions/counts,
PSNR +0.000515 dB, mapper time +14.49%. The cap materially changes timing.

## Historical D check (2/2 completed)

Historical D retains recent512/dense1024 and its previous CPU64/GPU16 dense
caches plus resident keyframes. Compared against the first FIFO execution:

| Scene | Historical PSNR | FIFO PSNR | Δ PSNR | Historical mapper s | FIFO mapper s |
|---|---:|---:|---:|---:|---:|
| aria | 25.655048 | 25.633404 | -0.021644 | 74.823 | 78.366 |
| rpng | 22.426583 | 22.423717 | -0.002866 | 106.253 | 112.183 |

Both pairs have identical image selection and admission sequences despite
390/896 historical candidate expirations. Thus candidate expiry did not change
actual training for these two scenes; this need not hold on longer streams.

This check confirms small observed quality differences from the prior D recipe.
The repeated full_ram/tiered comparison above is the primary timing result.

## Native frontend + mapper (2/2 completed)

Aria1253, one pair at seed0, 6,738 image-wise updates each. Native frontend remains
enabled with its own buffers. Same image selection, membership/admission/count
histories and reference camera poses; both audits pass. One pair is insufficient
to establish a general runtime advantage or statistical equivalence.

| Measurement | Full RAM | FIFO | Change |
|---|---:|---:|---:|
| Training service s | 37.038137 | 35.911077 | -3.04% |
| Mapper plus admission/dispatch/adoption s | 48.880906 | 53.699873 | +9.86% |
| Input/mapping stream s | 187.788142 | 191.451902 | +1.95% |
| Whole runner s | 193.716426 | 195.687307 | +1.02% |
| Held-out PSNR dB | 25.641313 | 25.638675 | -0.002637 dB |
| Peak process-tree VRAM GiB | 16.865234 | 19.992188 | +18.54% |

Additional timings (RAM → FIFO): image admission 0.0963→1.2566s; packet processing
8.3417→8.4689s; camera adoption/CPU-payload compaction 3.4048→8.0633s. Camera
adoption includes exact-pixel validation and storage access. Thus this measures
the shipped implementation including those checks, not an intrinsic limit of
FIFO or VRAM residency. Training service alone improves ~3%, but mapper plus
storage/admission increases ~9.86%, and the input/mapping stream increases ~1.95%.

The native training succeeded on the first attempt. Its first evaluator dispatch
incorrectly selected the shared-tape wrapper and was rejected at the budget
precondition, before rendering. The driver was corrected to the established
native 6N evaluator, reusing the unchanged map; evaluation and audit then passed.
The failed attempt/log remains in progress.json and the *_wrong_wrapper_failure.log.

## Timing scope

Shared-tape `mapper_seconds` includes RGB admission, packet replay/birth, view
preparation, selection, image-wise forward/backward/Adam, online topology and
heap release. It excludes decoding, startup, export and evaluator work; the exact
scope is in runtime.json. `whole_seconds` includes more surrounding runner work.

Historical native D `mapper_seconds` times training services only. The revised
launcher separately records image admission, packet dispatch/birth and camera
adoption, with CUDA synchronization at their boundaries. Their sum with the old
field is `mapper_with_admission_seconds`; it still excludes online topology outside
service, frontend work, intermediate snapshots and export. Native whole time is
reported separately. `input_mapping_stream_seconds` spans first RGB admission
through the last completed trainer call and excludes startup and terminal export.
Host copy/read counters must not be described as pure DMA.

## Artifacts

- Code: `benchmarks/online_gs/campaigns/03_benchmark_contract/replay_storage/`.
- Launcher: `benchmarks/online_gs/campaigns/03_benchmark_contract/mapper_recipe_d/run_d.py`.
- Paper: `paper/latex/sec/4_method_pip.tex`, Replay Implementation only; main.tex
  currently includes sec/4_method instead, and its include was not changed.
- Root: `/ssd/intern/paperExperiments/runs/campaigns/03_benchmark_contract/replay_storage/`.
- `20261011_smoke_v1`: forced SSD.
- `20261011_comparison_v1`: shared-frontend full_ram vs tiered_fifo, three scenes × two repeats.
- `20261011_legacy_v1`: historical bounded D, Aria/RPNG.
- `20261011_native_v1`: actual frontend+mapper Aria full_ram vs tiered_fifo.

Each run retains runtime, sample/count/admission ledgers, source hashes, final map,
held-out metrics and audit. The original D vendor bytes are unchanged. No speedup
or statistical quality equivalence is assumed from successful execution alone.
