# geometry(floater) 연구 이력 — 이 캠페인까지 (2026-10-13 정리)

5090에서 처음 보는 사람을 위해, 무엇이 어디에 있고 어떤 결론이 지금 방법을 만들었는지 순서대로 적는다.
숫자는 각 링크 문서의 것이며 여기서는 요약만 한다.

| 시기 | 무엇 | 결론 | 어디 |
|---|---|---|---|
| 2026-07 | batch 3DGS carve loss (exp38–47): 빈 공간 증거 score w·(1−maxop), softlite opacity 압력, 예산 top-K prune, 출생 gate, carve force | exp44d2에서 batch 품질과 floater 억제 동시 달성. floater는 두 집단(Pop1 init outlier / Pop2 densification) | [LEGACY](../00_legacy_foundations/README.md), [floater_populations](../../../knowledge/floater_populations.md), `3dgs-custom/eval/carve_loss.py` |
| 2026-08 | VIGS-SLAM 온라인으로 이식: exp55 내용 적응 예산 + carve, exp69 v7 verified-ray causal carve, exp70 detached opacity, exp71 termination loss, exp72 Carve×Hit | causal carve v7는 score 97.5%가 stale이라 실제 온라인 검증이 아니었음; Carve/Hit은 amplitude·routing 모두 lever이나 단일 run 판정은 노이즈(.19 dB) 안 | VIGS 브랜치 `exp69-latest-live-snapshot`, `exp72/carve-hit-loss-ablation`; aria-online-3dgs-bench `docs/HANDOFF_CHL_20260906.md`, `docs/KNOWLEDGE_REALTIME_GS_SLAM_FLOATERS.md` |
| 2026-09-01 | carve loss의 확률적 재정식화 설계 (Beta-Bernoulli 사후, −log T(D) 자유공간 NLL) | 코드 변경 없음; "튜닝 상수 13개 → 자유 파라미터 1개" 제안 | [research/carveloss_academic](../../../../research/carveloss_academic/README.md) |
| 2026-09-22~29 | DNGaussian식 soft/hard depth, rasterizer depth-backward 결함 수정(09-27), geometry 수렴·유지 캠페인, 외부 GT gate, capacity-matched freeze | depth→opacity routing이 geometry lever; 방법은 characterization으로 동결 | aria-online-3dgs-bench `docs/CAMPAIGN_SUMMARY_SOFT_PROXY_HARD_DEPTH_20260922.md`, `docs/HANDOFF_DNG_OBSERVABILITY_NORMAL_20260922.md` |
| 2026-09-30~10-01 | fixed40 merge S1–S17: dense frame depth transport(WG), anchoring, normal, 분포 기반 평가 | dense depth가 geometry를 고침; normal은 공중 Gaussian 14/15 감소 | VIGS main `scripts/selected_mapping/geometry_merge/` (README, PREREG_S*/S*_RESULTS), `docs/GEOMETRY_MAIN_VALIDATION.md`; main merge 6d200f0f(B 채택) |
| 2026-10-01~04 | floater 계열 S18–S50: offline evidence(S18A), FM 끝 정리(S21–S24), 근본 원인(S25–S28: BA 오류 출생·윤곽 spill·drift), 자기 일관 carve SEG2 → SEW3(S32–S37), cyan/pink 비교(S38), T+FM 검증 7/7(S42/S44) | **SEW3 + FM 채택**: held-out floater ×0.10–0.38, PSNR −.015~+.054, wall-clock +6~11% | VIGS 브랜치 `fixed40-geometry-merge` 4c51316: `geometry_merge/README_SELF_CARVE.md`, `PREREG_S18A…S38`, `S18A…S29_S36_RESULTS.md`, `PAPER_METHOD_CONSENSUS_CARVE_DRAFT.md` |
| 2026-10-07~09 | 팀원이 SEW3+FM을 **recipe C**로 통합(geometry_c, 4c51316 SHA 고정)하고 자체 frontend + 기준 pose + 6N 벤치마크로 B/C/D release | C = 우리 방법. TUM10 ablation: SEW3 PSNR ≈0, FM −.03 dB/−15% G | VIGS main 765d55d: `docs/CUSTOM_C_6N.md`, `docs/REPRODUCE_BCD.md`; [recipe_d](../06_gain_attribution/recipe_d/README.md), [geom_ablation_local](../06_gain_attribution/geom_ablation_local/README.md) |
| 2026-10-09~11 | **이 캠페인**: release C 위에 기존 방법 10개 공식 이식 + 학습 중 gradient 분해 probe + held-out/GT 라벨, 3장면 | 카테고리별 실패 지점 5가지 확정; 우리 선택성 1e4–1e6; GT 라벨은 한쪽만 셈 | 이 폴더, VIGS `handoff/floaterlab-baselines-20261013` |

## 용어 대응

- SEG2 / SEW3: self-consistency evidence carve. SEG2 = λ .2 gate 없음, SEW3 = λ 3 + persistence gate(.5→.8) + fast kernel. 코드 `FIXED40_SELF*`.
- FM(consensus finisher): export 시 현재 지도 KF 전체를 1회 렌더해 contribution≥.5, median-front share≥.8(margin .25)인 Gaussian 삭제. GT depth 미사용.
- T: terminal opacity<.1 prune. "T+FM"이 release C의 export 단계.
- floater 라벨(노랑∪파랑): held-out view에서 위 FM 규칙. 이 캠페인의 export floater.
