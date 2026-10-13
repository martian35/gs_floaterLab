# P04 — Carve Loss의 Incremental 이식 — 결과

> **append-only.** 기존 항목을 수정하지 말고, 정정이 필요하면 맨 위에 새 항목을 덧붙인다.
> 실패는 실패로 정직하게 기록한다 (프로젝트 원칙).

- **2026-10-13 — 이식 완료 및 baseline 기전 비교 (3090, seed 0).** carve의 incremental 이식은 SEW3(persistence-gated Consensus Carve) + FM(consensus finisher)으로 VIGS-SLAM-custom main에 **recipe C**로 채택되어 있다(`docs/CUSTOM_C_6N.md`, geometry_c, 4c51316 SHA 고정). 계획의 arm(① carve off ② v7-64 ③ 이식판) 중 ②는 측정하지 않았고, ① = base(C − carve − FM), ③ = C로 비교했다. 지표도 계획의 region GT AUC/AP가 아니라 held-out floater 라벨(FM 규칙, 학습에 안 쓴 view)·Kinect GT 라벨·gradient 분해 probe를 썼다. 결과: aria1253/table_06/TUM floater 44/6/16 → 3/0/3, PSNR ±.02 dB, 지도 0%; 기존 방법 10개(공식 이식)는 카테고리별 5개 실패 지점에서 막힘. **한계:** 외부 기준(Kinect, 앞쪽만 셈)에서는 ours = base(385 vs 384); seed 1개. → [GEO campaign](../../../context/experiments/campaigns/07_floater_mechanism/README.md), [knowledge](../../../context/knowledge/floater_baseline_mechanisms.md).
