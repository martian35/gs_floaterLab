# 기존 floater 억제 방법이 막히는 다섯 지점과 Consensus Carving의 답 (확정 결론)

> 근거: [GEO campaign](../experiments/campaigns/07_floater_mechanism/README.md) (3090, 2026-10-09~11, seed 0, aria1253/table_06/TUM fr1_desk).
> 마지막 갱신 2026-10-13. 결론이 뒤집히면 여기서 갱신하고 캠페인 문서 첫 줄에 `superseded` 표시.

| # | 막히는 지점 | 해당 카테고리 | 측정 근거 | 우리 방법의 답 |
|---|---|---|---|---|
| 1 | **opacity로는 floater와 표면이 구분되지 않는다** | 지도 관리 (MonoGS, 3DGS reset, 임계 prune) | 끝까지 남는 floater의 opacity .15–.36이 표면 분포 안; floater를 다 지우는 임계에서 표면 37–48% 소실; reset 후 floater도 표면처럼 재성장 | 판정 기준이 opacity가 아니라 **위치**(지도 자신의 median 표면보다 앞) |
| 2 | **앞/뒤 방향을 구분하지 않아 지우지 않고 옮긴다** | frontend depth 정규화, ray 통계 | depth gradient가 6배 커도 opacity 방향 중립(.54); 위치 gradient가 72–99% 뒤쪽이어도 실제 이동 3–5 cm(표면까지 12 cm+); CG-SLAM은 표면을 키워 조건 충족 | **앞쪽 질량에만, opacity만, 내리는 방향만** |
| 3 | **외부 깊이를 믿어 그 오차만큼 표면을 지운다** | 센서 free-space (GS-SLAM Eq.9, SplatAD, sensor carve) | frontend 깊이 vs Kinect 10% 일치 81.5% < 지도 90.6%; 같은 세기에서 표면 주입 ~1,000× → −1.6~−1.7 dB, 지도 −19~−29% (단, sensor arm은 KF view만·gate 없음이라 기준 깊이 단독 효과는 아님) | 기준이 **같은 지도의 median**이라 깊이 오차가 판정에 안 들어감 (대가: 지도-센서 불일치 미해결). **단 λ3에서 표면을 지키는 결정적 부품은 persistence gate다**(gate 없이는 우리도 −2.2/−2.4/−.9 dB; 기준 깊이의 몫은 선택성 2~3배, stage 12) |
| 4 | **지우는 세기와 지도를 지키는 세기가 양립하지 않는다** | DS-NeRF KL, SplatAD | floater/표면 힘 비율 1.2–7.3; 가중치 100배 낮춰도 table −8.7 dB; PSNR 지키는 세기에서 floater 효과 0 | gate 포함 선택성 1e4–1e6이라 λ 3에서도 표면 영향 0 (gate 없이는 646–1.8e3, PSNR −.9~−2.4 dB) |
| 5 | **되돌릴 수 없는 삭제** | 판정 후 삭제 (SparseGS, Sheng 2026) | SparseGS 삭제의 95%가 표면, −2.8 dB, 깊이 정확도 90.6 → 87.6%; Sheng 지도 −17~−42% | 학습 중 **soft gradient**(틀리면 RGB가 되돌림) + 끝에 누적 증거로만 삭제 |

## 같이 기억할 것

- **외부 기준 floater 라벨(GT depth 앞쪽만)은 지도 표면이 센서보다 앞인 곳을 센다**(걸린 것의 86–95%가 지도 기준 표면). 표면을 뒤로 밀거나 벗겨내는 방법이 유리해 보이므로 양방향 깊이 지표와 반드시 함께 낸다. 양방향(10% 일치율)에서는 모든 arm이 base ±0.3 %p 안이거나 아래다(GOF +0.26, cc+sensor +0.10 %p는 수치상 위; seed 1개라 판정 보류).
- 우리 라벨(지도 median 기준)은 우리 규칙과 같아 부분적으로 정의상의 결과다. 외부 기준에서는 우리 = base. 주장은 "깊이 정확도·화질을 해치지 않고 지도가 스스로와 모순되는 floater를 지운다".
- floater 원시 개수는 지도를 줄이기만 해도 준다(MonoGS). 비율(보이는 Gaussian 1,000개당)과 지도 크기·PSNR을 같이 본다.
- **persistence gate가 Consensus Carving의 안전장치다.** 같은 λ3에서 gate만 끄면 표면 주입 90~4,600배, PSNR −2.2/−2.4/−.9 dB, 양방향 깊이 일치 90.6 → 87.2%(SparseGS 수준). "자기 median 기준"만으로는 부족하다.
- 학습 중 carve와 끝의 FM은 하는 일이 다르다: carve는 학습 중 지도(−19%/−62%), FM은 잔여. aria에서는 둘 다 필요, TUM은 FM이 대부분.
- 캠페인 운영 교훈: 뒤 단계를 "앞 단계 출력 N줄"로 기다리면 앞 단계가 하나라도 실패할 때 영원히 대기한다. 한 스크립트에서 순서대로 호출한다.
