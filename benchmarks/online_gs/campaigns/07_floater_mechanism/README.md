# GEO campaign — runner

실행 코드는 VIGS-SLAM-custom 브랜치 `handoff/floaterlab-baselines-20261013`의 `scripts/floaterlab/`에 있다
(release C 실행기 위의 plugin이라 VIGS 저장소에 두었다). 실행 안내: VIGS `docs/FLOATERLAB_BASELINES.md`.

`jobs_3090/`: 3090 캠페인에서 실제로 쓴 단계별 작업 목록(`jobs_stage*.json`, campaign.py 입력)과 체인 스크립트. 경로는 3090 기준이며
5090에서는 `scripts/floaterlab/jobs/make_jobs.py`로 다시 만든다. 단계 순서: 1 aria1253 내부 ablation → 2 DNGaussian/지도 관리/Sheng/SparseGS →
3 TUM 8 arm + GS-SLAM → 4–5 table_06 전체 + 새 방법 4개 → 6–7 KL/SplatAD 가중치 스윕과 전이 → 8 우리 분해 → 9 sensor carve λ3 → 10 fm_only 재실행 → 11 GT 라벨 감사·조합.
`stage9_chain.sh`/`stage10_chain.sh`는 출력 줄 수 대기로 교착했던 버전(기록용), `stage9_10_chain.sh`/`stage11_chain.sh`가 한 스크립트 순차 호출로 고친 버전이다.
