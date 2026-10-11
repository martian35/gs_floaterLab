# F10 — 내용 기반 삽입의 Gaussian 수–PSNR 절충 (UTMM)

먼저 [한국어 제작 계획](plan/CURRENT.md)을 읽는다. [전체 목록](../README.md).

2026-10-11: **제작 계획 / 최종 그림 미제작**. 실험 수치와 colin 재현 절차만 정리했다.

UTMM 8장면에서 새 Gaussian의 생성 밀도를 0.5–1.5배로 바꾸며, 균등 삽입과 내용 기반 삽입(C의 online rank 초기화,
아래 I)의 최종 Gaussian 수와 held-out PSNR을 비교한다. 기준점은 균등 삽입·밀도 1이다.
8장면 평균에서 I·밀도 0.75는 Gaussian −32.6%, PSNR +0.207 dB, LPIPS −0.006이며 8/8 장면에서 PSNR이 기준 이상이다.

2026-10-11 colin 재현 완료(RTX 5090, 73 run): 로컬 대비 run별 PSNR 차이 최대 0.031 dB, I·밀도 0.75 평균 −32.7% / +0.203 dB / 8/8.

- `plan/`: 버전별 계획과 CURRENT.md.
- `analysis/`: 로컬 RTX 5070 Ti run 집계([결과 스냅샷](analysis/RESULTS_SNAPSHOT.md)), 원값 CSV, provenance.
- `repro/`: colin 재현 절차와 패치된 ablation 하네스([재현 방법](repro/README.md)). colin 코드는 수정하지 않는다.
- `scripts/`: 집계 코드(`summarize_utmm_screen.py`). 그림 builder는 아직 없다.
- `candidates/`, `output/`: 검토본(아직 없음). `current/`: 검수한 최종본만. 아직 최종본 없음.

- [실험 카드](../../../context/experiments/campaigns/06_gain_attribution/utmm_scene_screen/README.md)
- 선행 실험: [밀도×예산](../../../context/experiments/campaigns/06_gain_attribution/geom_ablation_density/README.md),
  [예산 1N/2N/6N](../../../context/experiments/campaigns/06_gain_attribution/geom_ablation_init/README.md).
