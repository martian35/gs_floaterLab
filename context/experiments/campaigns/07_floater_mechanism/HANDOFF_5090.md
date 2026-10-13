# 5090에서 이어가기 (2026-10-13)

## 가져올 것

| 저장소 | 브랜치 | 내용 |
|---|---|---|
| sawo0150/VIGS-SLAM-custom | `handoff/floaterlab-baselines-20261013` | main d3b57506 + `scripts/floaterlab/` + `docs/FLOATERLAB_BASELINES.md` |
| sawo0150/gs_floaterLab | `handoff/floater-mechanism-20261013` | 이 캠페인 폴더, knowledge, 경량 결과, STATUS/INDEX 항목 |

둘 다 main에 merge하지 않았다. 검토 후 merge한다.

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
