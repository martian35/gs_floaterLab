# F10 — colin 재현 방법

목적: `analysis/utmm_2N_reference_start/`(로컬 RTX 5070 Ti)와 같은 UTMM 8장면 × 9 arm 실험을 colin에서 다시 돌린다.
**colin의 기존 코드는 수정하지 않는다.** 패치된 geometry-ablation 하네스만 별도 폴더에 복사하고,
나머지 하네스(`mapper_equal_render`, `mapper_baselines`)와 VIGS-SLAM-custom은 colin의 현재 파일을 읽기 전용으로 쓴다.

## 코드 상태 (2026-10-11 확인)

- `/home/intern/VIGS-SLAM-custom`: HEAD `4ad39496`, 미커밋 diff sha256 `fff600c0…`(591줄) — 로컬 run과 동일.
- `03_benchmark_contract/mapper_equal_render`, `mapper_baselines/v2`의 `.py` 330개 — 로컬 snapshot과 sha256 동일
  (`colin_siblings.sha256`).
- 하네스 실행 중에는 `run_arm.py`의 `verify_recipe`가 C recipe source lock을 다시 검사한다. recipe가 바뀌면 run이 시작하지 않는다.
- `bash check_sources.sh`로 위 세 가지를 읽기 전용으로 확인한다.

## 패치 (`harness/mapper_geometry_ablation/`, 원본 대비 diff는 `patches/`)

colin 2026-10-09 원본(`colin_original_ablation.sha256`) 대비 변경. 기본값은 모두 원본 동작이다.

| 파일 | 변경 | F10에서 쓰는 설정 |
|---|---|---|
| `run_arm.py` | `ABLATION_RPI`로 예산 배수 선택(기본 6N); `--arm`에 plan의 임의 arm 허용; `ABLATION_REFERENCE_START=1`이면 IMU 초기화 전 지도 시작(colin UTMM C `run_custom_c_reference_start.py`와 같은 정책) | `ABLATION_RPI=2`, `ABLATION_REFERENCE_START=1` |
| `ablation_support.py` | `ABLATION_PLAN` 경로; arm별 `density_scale`(두 방법에 같은 `pcd_downsample` 역배율); 균등 초기화 패치가 래퍼 사슬 가장 안쪽 메서드를 바꾸도록 수정(원본은 online-density 래퍼에 막혀 실패); `ABLATION_FM_SKIP_NODEPTH`(F10에서는 끔) | plan의 arm |
| `evaluate_stages.py` | `ABLATION_ALLOW_NO_DEPTH=1`이면 depth GT 없는 장면 통과(UTMM은 depth GT 없음) | 켬 |
| `audit_arm.py` | 6N 고정 검사를 계약의 예산 배수로 | — |
| `run_suite_utmm.py` | `run_suite.py` 기반 F10 대기열: arm 순서, depth 지표 없을 때 요약·파일럿 비교 허용 | — |

`plan_utmm_2N.json`: arm 정의(R4 tape capture, `R2@s`/`R2-I@s`, s ∈ {0.5, 0.75, 1, 1.5}).

## 절차

```bash
cd /home/intern/gs_floaterLab/paper/figures/figure10_insertion_density/repro
bash setup_and_run.sh prepare     # CPU. 소스 확인 → /home/intern/gs_floaterLab_figure10_repro/ 생성 → suite 폴더 생성
bash setup_and_run.sh run         # GPU. 73 run(학습 72 + 파일럿 재생 1), 로컬 5070 Ti 기준 약 1.2시간
bash setup_and_run.sh summarize   # CPU. runs.csv / mean_by_arm.csv, 로컬 run과의 장면별 PSNR 차이
```

- 출력 기본 위치: `/ssd/intern/paperExperiments/results/campaigns/06_gain_attribution/figure10_utmm_insertion_density/2N_reference_start`
  (`F10_OUT`으로 변경). repro 트리는 `F10_REPRO`로 변경.
- `gpu_exception.json`은 어떤 프로세스도 면제하지 않는 receipt다. 다른 GPU 작업이 있으면 하네스가 기다린다.
- 하네스의 디스크 보호(여유 24 GiB 미만이면 중단)가 그대로 동작한다. frontend tape는 suite 폴더 `frontend_cache/`에 쌓이며
  정상 종료 후 지워도 된다(요약에 필요 없음).
- **GPU run은 사용자 승인 후에만 실행한다.** 이 문서는 절차만 기록했고 colin에서 실행한 적은 없다.

## 판정 기준

- 파일럿: square-1 tape 재생이 `pilot_frontend_equivalence.json`에서 통과해야 나머지가 돈다.
- 로컬 결과와의 비교는 같은 실행 안의 **기준 대비 변화**로 한다. 로컬에서 지도 시작 조건만 바꾼 두 실행 사이에
  절대 PSNR이 평균 0.13 dB(최대 0.26 dB) 달랐지만 I0.75 − U1은 0.05 dB 이내로 같았다.
- 재현 성공 기준(제안): I0.75가 8/8 장면에서 U1 이상, 8장면 평균 ΔPSNR이 +0.21 ± 0.05 dB, ΔGaussians가 −33 ± 3%.
