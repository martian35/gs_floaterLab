# 5090에서 이어가기 (2026-10-13)

## 가져올 것

| 저장소 | 브랜치 | 내용 |
|---|---|---|
| sawo0150/VIGS-SLAM-custom | `handoff/floaterlab-baselines-20261013` | main d3b57506 + `scripts/floaterlab/` + `docs/FLOATERLAB_BASELINES.md` |
| sawo0150/gs_floaterLab | `handoff/floater-mechanism-20261013` | 이 캠페인 폴더, knowledge, 경량 결과, STATUS/INDEX 항목 |

둘 다 main에 merge하지 않았다. 검토 후 merge한다.
2026-10-13 현재 gs_floaterLab 브랜치는 **fork `martian35/gs_floaterLab`**에 있다(martian35는 sawo0150/gs_floaterLab 읽기 전용이라 push 거부).
5090에서: `git fetch git@github.com:martian35/gs_floaterLab.git handoff/floater-mechanism-20261013:handoff/floater-mechanism-20261013`,
또는 sawo0150이 fork에서 PR을 받는다. 같은 내용의 git bundle이 3090 `vigs_aria_experiments/handoff_20261013/`에도 있다.

## 순서

1. **설치**: `docs/FLOATERLAB_BASELINES.md` §설치. diptest 설치, GOF·CG-SLAM arm을 돌릴 거면 공식 rasterizer 두 개 빌드(`official_builds/fetch_and_build.sh`).
   공유 env에 넣을지 복제 env + `VIGS_REPRO_STATE`로 격리할지 env 소유자와 정한다.
2. **패리티**: `arms/cc.json`을 aria1253에 돌려 release C와 PSNR이 ±.03 dB 안인지 확인. 다르면 fingerprint/rasterizer가 다른 것이다.
3. **핵심 arm**: `base cc carve_only fm_only monogs dngaussian cgslam gsslam_eq9 sparsegs` (대표 7 + 분해 2). 5090에서는 seed 0,1,2로.
4. **외부 기준 지표**: GT depth가 있는 장면(TUM, ETH3D)에서 `label.py --anchor gt` **와** `analysis/surface_vs_gt.py`(양방향 10% 일치율)를 같이 낸다. 한쪽 지표만 내지 않는다.
5. **표**: `summarize.py` → `analysis/main_table.py` (TeX 포함).

## 5090 벤치마크에서 더 할 것 (3090에서 못 한 것)

- seed 3개 (3090은 1개). 장면 추가(ETH3D sofa_1, UTMM은 reference-start 실행기라 arm 미지원 — `launch.py`가 거부한다).
- SparseGS를 공식 설정처럼 스트림 2/3 지점에서 삭제 후 1/3 회복 학습으로 다시 돌리기 (지금은 export 시 삭제, 회복 없음).
- Sheng 2026 감쇠 정밀도 (학습 중 감쇠라 삭제 직전 지도가 없다; 감쇠 시점 ID 기록 필요).
- 팀원 TUM10 geometry ablation([geom_ablation_local](../06_gain_attribution/geom_ablation_local/README.md): SEW3 PSNR ≈0, FM −.03 dB/−15% G)과
  floater‰ 지표를 같은 run에서 같이 내면 "PSNR 중립 + floater 감소"가 한 표에 들어간다.

## 팀원 작업과의 관계

팀원의 View Pool / Initialization / frame selection(ATTR campaign, recipe D)은 **base의 일부**다. floaterlab은 그 위에 geometry만 바꾸므로
recipe D 실행기로 base를 옮기려면 `run_arm_worker.py`의 실행기 모체(지금은 `run_custom_c_large_pool_6n.py`)를 D 실행기로 바꾸고
`floaterlab_runtime.install/finish`를 같은 지점에 끼우면 된다. arm JSON과 methods는 그대로 쓸 수 있다.

## 2026-10-13 — 5090 검토(읽기 전용 확인) 반영

- **실행 장애:** VIGS main d3b57506의 `reproduction/release_manifest.json`이 `scripts/selected_mapping/test_floater_export.py`(d66d8a3c에서 변경)와 불일치해 `verify_source()`가 실패한다.
  VIGS 브랜치 `handoff/floaterlab-baselines-20261013`에서 해당 해시를 갱신했다. **main에도 같은 한 줄 수정이 필요하다.**
- **새 worktree runtime:** `.reproduction/runtime.json`은 worktree마다 있다. 재사용(`VIGS_REPRO_STATE=<publish 디렉터리>/.reproduction`) 또는 재빌드(`install_cuda.sh` + `configure.py`). VIGS `docs/FLOATERLAB_BASELINES.md` §설치.
- **추가 패키지:** 두 env(vigs-slam-5090, vigs-mapper-5090) 모두 diptest·gof_rasterization·cgslam_rasterization 없음, lpips 있음, nvcc 12.8 = torch cu128.
- **해석 정정 3건** (hub·gt_label_audit·ours_decomposition·knowledge에 반영): ① 양방향 10% 일치율은 모든 arm이 base ±0.3 %p 안이거나 아래(GOF +0.26 %p가 최대) — "어떤 방법도 넘지 못했다"는 틀림. ② sensor λ3의 GT floater는 "지도를 유지한 arm 중" 최저(KL w.1·SplatAD w1은 더 낮으나 지도 붕괴). ③ sensor carve 비교는 기준 깊이·KF-only·gate 유무가 함께 다름 → gate 대조 arm `cc_nogate` 추가(3090 stage 12, 결과는 ours_decomposition §4).
- **통합 시 겹치는 파일:** lab `context/STATUS.md`, `context/experiments/INDEX.md`, `context/experiments/README.md`, `campaigns/README.md`, `paper/experiments/P04_carve_incremental/result.md`; VIGS `CUSTOM_README.md`. 내용 단위로 merge한다.
- GEO arm 실행기는 recipe **C** 기반이다. 최신 D·replay storage 위에서의 geometry ablation으로 해석하지 않는다.

## 2026-10-13 — 최신 baseline(D) 위에서 돌리기

- VIGS 브랜치 7c17993b: `launch.py --recipe-base D --arm <arm.json>`. 팀 D addon(`mapper_recipe_d/vendor/d_recipe_shim.py`, scale cap .5 + 덮인 출생 .02)을
  run_d.py와 같은 순서로 우리 worker에 씌운다. arm JSON은 그대로: `base.json` = D − SEW3 − FM, `cc.json` = D. `make_jobs.py --recipe-base D`.
- 5090 순서: ① `launch.py --recipe D`(release D)와 `--recipe-base D --arm cc.json` 패리티(±.03 dB) ② `base cc carve_only fm_only monogs dngaussian cgslam gsslam_eq9 sparsegs`를 D 위에서 seed 0,1,2.
- 3090 파일럿 결과([results_D_pilot](results_D_pilot/README.md)): D 경로 동작, PSNR 패리티 aria −.005 dB(TUM +.04, 경계 밖 → 5090에서 재확인), Gaussian +1.2%/+.5%.
  D는 base floater를 2.7~3배 줄이고(44 → 16, 16 → 5), 우리 효과는 유지된다(cc_D 1/0, PSNR ±.01). 절대 수가 작으므로 5090에서 seed 3개·장면 추가가 필요하다.
- tiered FIFO replay storage(gs_floaterLab `replay_storage/run_mapper.py`)는 아직 floaterlab에 연결하지 않았다(팀원 검증: 품질 Δ ≤ .016 dB).
