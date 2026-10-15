# §3.3 Consensus Carving — 작성 브리프 (2026-10-15, 5090 인계용)

> 읽는 사람: §3.3을 실제로 쓸 사람(5090 세션). 이 문서는 "무엇을, 어떤 순서로, 어떤 근거로 쓸 것인가"를 정하고,
> 숫자의 출처를 가리킨다. 본문 문장은 여기 없다. 문단은 이 브리프에 합의한 뒤 하나씩 쓴다.
> 입력: `paper/latex/sec/4_method_pip.tex`(팀원이 쓴 §3.1·§3.2 = 스타일 기준; 현재 §3.3은 2026-10-04 초안 → **무시하고 새로 쓴다**),
> 근거: `context/experiments/campaigns/07_floater_mechanism/`(GEO campaign), 이론 정리: 이 문서 §4.

## 0. 한 줄 요약

§3.1–3.2가 "어떤 view를 언제 학습하는가"를 정한 뒤, §3.3은 그 학습이 끝내 지우지 못하는 Gaussian(틀린 깊이에서 태어나 모순 view를 거의 못 만나는 것)에
**지도 자신의 ray median을 기준으로, 앞쪽 기여에만, opacity에만, 여러 view에 걸친 지속성으로 가중한, 되돌릴 수 있는 압력**을 주는 항을 더한다.
구조의 근거는 2026-10-09~13 기전 캠페인이다: 선택성의 주 부품은 **persistence gate**(100~1,000배), 자기 median 기준은 **부 부품**(3~7배)이다.

## 1. 스토리라인 (문단 = `\paragraph`, 첫 문장은 모두 "We …")

```
P0  틀린 깊이에서 태어나 모순 view를 거의 못 만나는 Gaussian은 base 목적함수에 보이지 않는다 (문제).
        ▼  "보려면 ray 위 질량 분포가 필요하다"
P1  종료 가중치 w_ri를 ray의 질량 분포로 읽는다 (표기).
        ▼  "기준은 이 분포의 median이다"
P2  consensus depth = ray 질량의 median; 절반 미만은 못 움직이고, dense 초기화 덕에 틀린 출생은 자기 ray에서 소수다.
    (외부 깊이를 쓰지 않는 이유는 한 절: 출생 깊이를 기준으로 쓰면 그 출생은 벌점 0이다.)
        ▼  "이 기준 앞의 질량에 opacity 벌점을 준다"
P3  합의 앞 기여 f_i를 세고 투과율·합의를 고정한 채 opacity logit에만 gradient를 준다 (수식 3·4).
        ▼  "왜 opacity인가 — 자연스러운 대안은 옮기는 것이다" (유일한 반론 형식)
P4  앞 질량은 위치에 대해 조각상수이고, 합의는 view마다 다른 점이며, 도착지는 이미 설명된 표면이다;
    opacity 감소는 view 무관·한 차원·가역이다. 그래서 (4)는 모순을 방향이 아니라 소멸로 번역한다.
        ▼  "한 view의 앞 판정은 증거의 일부일 뿐이다"
P5  Gaussian이 보인 모든 view에 걸친 앞 비율 F_i/V_i로 gradient를 가중한다; 얇은 구조·경계·새 표면이
    일부 view에서 앞에 놓이는 것을 걸러내는 부품이다 (성질로 진술; "핵심"임은 §5가 말한다).
        ▼  "증거는 누적되고 압력은 가역이다"
P6  매 render에 작용하는 연속 압력이라 첫 모순 view부터 작동하고, 틀리면 photometric 항이 되돌린다
    (판정·삭제와의 대비는 한 절, 인용 하나).
        ▼  "삭제는 export에서 한 번"
P7  opacity 임계 + 막판 keyframe 출생에 대한 증거 read-out (consensus finisher).
        ▼
P8  비용과 L_map = L_base + L_cc.
```

왜 이 틀인가: 2DGS·GOF·Mip-Splatting·MonoGS의 regularizer 소절은 모두 "동기 → 정의 → 수식 → 선택의 근거(한 절씩) → 총 목적함수"로
**자기 방법을 세우는 글**이고, 대안 대비는 한 문단에 한 절(Mip-Splatting vs EWA는 한 문단)이다. 대안 기각을 연속으로 쓰면 §2와 겹치고,
"아니다"마다 §5 증명이 필요하며, 방어적으로 읽힌다. 그래서 네 대안(외부 깊이 / 위치 이동 / view별 판정 / 삭제)은 **ablation 표의 숨은 뼈대**로만 쓰고,
본문에서는 P2·P5·P6에 한 절씩, P4에만 반론 형식 한 문단을 허용한다.

## 2. 왜 이 구조인가 — 근거 (숫자는 aria1253 / table_06 / TUM, 3090 seed 0; 출처는 GEO campaign 카드)

| 설계 결정 | 근거가 된 측정 | 수치 | 출처 |
|---|---|---|---|
| P0 문제: 남는 Gaussian은 base 항에 보이지 않는다 | survivor는 오래 살고(마지막 10% 출생 16%) opacity 중앙값 .24(.15–.36)로 표면 분포(.13–.99) 안; RGB fade share .49(표면 .47), geometry 항 .58(.53) | — | `mechanism_probe/README.md` §1 |
| P2 기준 = 자기 median, 외부 깊이 아님 | frontend 깊이는 Kinect와 10% 일치 81.5% < 지도 표면 90.6%; 같은 λ.2·gate 없음·FM 없음에서 자기 median이 frontend 기준보다 PSNR 손실 2.5~3배 작고 선택성 3~7배 | −.06/−.04/−.01 vs −.15/−.11/+.01 dB | `ours_decomposition/README.md` §5, `gt_label_audit` |
| P4 opacity만: 옮기는 항은 지우지 못한다 | DNG hard 위치 gradient 72% 뒤쪽·GOF 99% 뒤쪽이지만 실제 이동 3~5 cm(표면까지 12 cm); floater 수 그대로(43/32/11, 42/7/15 vs base 44/6/16) | — | `mechanism_probe` §1, `results_3scenes` |
| **P5 지속성 가중이 안전성의 주 부품** | cc에서 gate만 끄면(λ3) 표면 주입 90~4,600배, PSNR −2.23/−2.39/−.92 dB, 선택성 3.6e5/6.1e6/1.1e4 → 1.8e3/1.3e3/646; 양방향 깊이 일치 90.6 → 87.2% | — | `ours_decomposition` §4 (stage 12) |
| P6 연속 압력 vs 판정·삭제 | SparseGS 삭제의 95%가 표면, held-out 기여 24–33% 손실, −2.8 dB; Sheng 지도 −17~−42% | — | `mechanism_probe` §4 |
| P7 finisher의 역할 | carve만 8/0/8, FM만 11/0/2, 둘 다 3/0/3 (base 44/6/16); TUM은 FM이 대부분 | PSNR ±.02 | `ours_decomposition` §1 |
| 지도 관리(opacity 임계)로는 안 되는 이유 (§5 분석용) | 임계 t에서 지워지는 비율 survivor/표면: .2 → .32/.16, .5 → 1.0/.37; MonoGS 지도 −67~−81% | — | `mechanism_probe` §3 |
| 최신 baseline(D) 위에서도 유효 | D는 base floater 2.7~3배 감소(44→16, 16→5); cc_D 1/0, PSNR ±.01 | — | `results_D_pilot/README.md` |

주의(본문에 쓰지 말 것): seed 1개; 우리 floater 라벨은 우리 규칙과 같다(순환); Kinect 기준 한쪽 라벨에서 ours = base; 양방향 일치율에서 base를 유의하게 넘은 arm 없음.
→ 주장은 "깊이 정확도와 화질을 해치지 않고, 지도가 스스로와 모순되는 floater를 지운다"까지.

## 3. 문단별 사양

| # | 제목(가안) | 첫 문장의 주장 | 이론(본문) | 대비(한 절) | 수식 | 분량 | 쓰지 말 것 |
|---|---|---|---|---|---|---|---|
| P0 | (도입) | 3.1–3.2의 학습으로도 남는 Gaussian이 있다 | opacity 겹침·photometric 중립 → base 항에 불가시 | — | — | 50 | 수치 |
| P1 | Ray termination | w_ri를 ray의 종료(질량) 분포로 읽는다 | 표준 합성식; D_r은 seeding·base에만 | — | (1) | 70 | — |
| P2 | Consensus depth | 기준은 ray 질량의 median이다 | median breakdown ½; dense init → 틀린 출생은 소수; 출생 깊이 기준이면 벌점 0(순환) | 2DGS T=.5 pivot(사후) vs 우리(학습 중 고정 기준); GGGS(미분) | (2) | 120 | "센서 오차가 안 들어간다"를 주 효과로 쓰지 말 것 |
| P3 | Carving term | 매 render에서 앞 기여를 세어 opacity logit에만 벌점 | f_i = 종료 분포 아래 "합의 앞에서 끝날 확률"; T·d* 고정 | — | (3)(4) | 130 | — |
| P4 | Opacity, not displacement | 자연스러운 대안은 합의로 옮기는 것이다 | (a) indicator → 위치 gradient 0, 옮기려면 depth-matching 손실(모든 Gaussian 같은 부호) (b) 합의는 view별 점 → 다른 view에선 여전히 앞 (c) 도착지는 이미 설명된 표면, 틀린 색 (d) 가역·한 차원 | depth loss 계열 한 절 | 없음(명제 1줄) | 130 | 예산(LR) 논거는 Supp |
| P5 | Persistence weight | 모든 view에 걸친 앞 비율로 가중한다 | per-view 플래그는 얇은 구조·경계·새 표면에서 거짓 양성; F/V는 증거 누적; τ0=.5, τ1=.8 | 이력 점수를 판정 입력으로 쓰는 RTG-SLAM/VINGS-Mono | (5) | 100 | "핵심 부품" 단정(§5 인용으로) |
| P6 | Continuous pressure | 첫 모순 view부터 작동하고 틀리면 되돌려진다 | 모순 증거 희소·지연; 삭제 비가역 | SparseGS/Sheng 한 절 | 없음 | 70 | 수치 |
| P7 | Pruning and consensus finisher | 삭제는 export에서 한 번 | 막판 KF는 render 부족; finisher = 같은 증거 read-out, 유일한 판정 | MonoGS opacity 임계 | 규칙 | 90 | — |
| P8 | Cost | render 0 추가, 스칼라 2개, 커널 1개 | — | — | (6) | 50 | ms 수치는 표 |

합계 ≈ 810 단어(목표 ≤ 750: P2·P4에서 줄인다). 그림 1개: ray 토이(위치 gradient의 부호 공통 vs opacity gradient; 현재 Fig.~ray 재사용).

## 4. 이론 메모 (상태 표기)

| 명제 | 상태 | 비고 |
|---|---|---|
| median breakdown: ray 질량의 ½ 미만인 어떤 집합도 d*를 자기 위치로 못 옮긴다 | 증명됨(정의) | 토이에서 a_f=.5일 때 d*가 floater로 끌림(한계) |
| 합의 앞 질량 Σ w·1[z<(1−ρ)d*]는 z에 대해 조각상수 → 자연 gradient는 opacity 경로뿐 | 증명됨 | P4 (a)의 근거 |
| 앞 질량의 a_rj에 대한 정확한 도함수 = T_rj·T_r(B)/T_r,j+1 → 불투명 군집의 앞 Gaussian에서 0; T 고정이 군집을 앞에서부터 벗긴다 | 증명됨(유도 Supp A) | 2026-10-04 검토 |
| 렌더 깊이 손실의 위치 gradient는 ray 위 모든 Gaussian에 같은 부호 (∂D̄/∂z_i = w_i/A > 0) | 증명됨 | P4 |
| 합의 깊이는 view·ray별 양이라 틀린 출생에는 모든 view를 만족하는 단일 3D 목적지가 없다 | 논증(측정 간접: Hit online 표면 도달 7%) | consensus-pull control arm 미실행 |
| 위치 vs opacity 예산: position lr 1.6e-4×scale(실효 ~1e-3 m/step) vs opacity lr .05; 12 cm ≥ 100 step vs logit 1.35 ≈ 27 step | 계산(Adam 상한 근사) | Supp 또는 각주 |
| per-view 앞 플래그는 신뢰할 수 없는 판정; F/V 누적이 선택성 100~1,000배를 만든다 | 측정(stage 12) | 본문은 성질로, 크기는 §5 |
| 자기 median 기준의 몫 3~7배 | 측정(stage 14) | P2는 한 절 |
| (P1) z_ri = D_r에서 태어난 Gaussian에 D_r 기준 free-space 손실의 gradient는 0 | 증명됨 | 순환성 |
| (P2) d* 고정 시 ∂L_cc/∂ℓ_i ≥ 0, ray 질량 절반 초과가 z/(1−ρ) 뒤에서 끝나면 양수 | 증명됨 | 순서 불변 과장 금지(2026-10-04 검토 #2) |

## 5. 직관의 흐름 (왜 이렇게 되었나, 시간순)

1. 2026-08: BA 깊이 기준 carve(CHL, exp69 v7). 센서 기준은 출생을 지지하고(순환) 깊이 오차가 표면 손실이 됨을 봄.
2. 2026-10-01~03: 자기 일관 carve SEG2(λ .2, gate 없음) → 대부분 장면에서 floater 감소하나 일부 장면 PSNR 비용 → gate 추가한 SEW3(λ3)가 5장면에서 PSNR ≥0.
3. 2026-10-02: 막판 KF 출생이 남는 구조적 이유 → FM finisher.
4. 2026-10-07~09: 팀원이 SEW3+FM을 recipe C로 채택, B/C/D 벤치마크.
5. 2026-10-09~11: 기전 캠페인 — 기존 방법 10개 공식 이식 + gradient 분해. 카테고리별 실패 지점 5개.
6. 2026-10-13: gate 대조 → **gate가 안전성의 주 부품**; 기준 깊이 대조 → 자기 median은 부 부품(3~7배). 이전 "센서 오차 때문" 해석을 정정.
7. 2026-10-13: D 파일럿 — D의 덮인 출생 .02가 base floater를 3배 줄이고, 우리 항은 나머지를 지움(보완 관계).

## 6. Method ↔ Experiments 짝

| 본문의 성질 | §5 행(ablation) | 상태 |
|---|---|---|
| P2 자기 median 기준 | sensor_carve λ.2 / λ3, carve_l02_nogate | 3090 완료 |
| P4 opacity만 | DNGaussian(hard/soft), GOF distortion, d4; **consensus-pull control(미실행, 권장)** | 부분 |
| P5 지속성 가중 | cc_nogate | 3090 완료 |
| P6 연속 압력 | SparseGS, Sheng 2026 | 3090 완료(Sheng 정밀도 미측정) |
| P7 finisher | carve_only, fm_only | 3090 완료 |
| 전체 | base / cc / 대표 5 방법 × 3장면 × seed 3 on D | 5090 진행 중 |

§5에 "Why prior terms fail" 분석 소절(선택성 표 + survivor 프로파일)을 두는 것을 권한다. 기전 수치는 모두 거기로.

## 7. 고쳐야 할 불일치 (저자 결정 필요)

1. **서론 69·83행**: "Carve loss uses currently available **keyframe depth estimates**" → 이것은 sensor 기준 방식이다. "the map's own rendered consensus"로 바꿔야 한다. 세 번째 기여 bullet도 같이.
2. `plan/claims/CURRENT.md` D절: D3("incremental에서도 같은 효과") 근거가 생겼다(C·D 하네스, 3장면 seed 0; 5090 seed 3개 대기). 새 claim 후보: "persistence gate가 λ3를 안전하게 만든다"(stage 12), "기준 깊이의 몫은 부"(stage 14). `newver.sh`로 버전 업은 저자가.
3. §2.3 Geometric Convergence and Floater Suppression: StableGS·SplatAD·GS-SLAM·SparseGS·Sheng 대비 문장이 P2/P4/P6의 한 절과 중복되지 않게 분배.
4. Supp A: 명제 3개 유도 + 3-floater 군집 예 + LR 예산 계산.
5. 현재 §3.3 초안의 "a single λ=3 holds on all our sequences" → §5 인용으로. "We need neither a sensor nor a second render"는 유지 가능(사실).

## 8. 글쓰기 규칙 (팀원 §3.1–3.2에서 추출)

- 문단 첫 문장 "We …"로 무엇을 하는지; 그다음 선행이 부족한 이유(인용) → 기전 → 수식 → 값의 이유.
- 수치는 그림을 가리킬 때만; 나머지는 "Sec. 5". 과장 방지 문장은 `%` 주석으로 남긴다(예: "3:3:6은 system setting").
- 선행 대비는 소절당 한두 문장. 인용 키는 `litreview_floater_20261004/phase2_verification/verified_sources.md`의 것만.
- 용어 고정: consensus depth d*_r, consensus carving L_cc, persistence weight ω_i, opacity read-out, consensus finisher. SEG2/SEW3/FM/self-carve/floaterlab은 본문 금지.

## 9. 5090에서 시작하는 순서

1. 이 브리프와 `4_method_pip.tex` §3.1–3.2를 읽는다. 현재 §3.3은 표기·수식 번호만 참고.
2. P0 한 문단만 쓴다(50 단어). 검토 → P1·P2 → … 한 번에 한 문단.
3. 각 문단 아래 `%` 주석으로: 근거 카드 경로, 쓰지 않은 주장, 리뷰어 예상 질문.
4. 전부 쓴 뒤 분량(≤750)과 §2.3 중복을 점검하고, 불일치 목록(§7)을 저자에게 보고한다.

## 10. 참고한 논문 구조

2DGS §5 Training (https://arxiv.org/html/2403.17888v2), GOF §3.3 (https://arxiv.org/html/2404.10772v2),
Mip-Splatting §5 (https://ar5iv.labs.arxiv.org/html/2311.16493), MonoGS §3.3 (https://arxiv.org/html/2312.06741),
MIT CommLab Methods (https://mitcommlab.mit.edu/eecs/commkit/journal-article-methods-cs/), SIGGRAPH structure guide (https://research.siggraph.org/blog/guides/how-do-i-structure-a-paper/).
