# 더함 브랜드 필름 (47.5초)

더함화재특종손해사정 홍보 영상. 브랜드 한 줄: **빠진 것을, 더합니다.** · 공식 태그라인: 손해의 근거, 회복의 방향.

| 파일 | 용도 |
|---|---|
| `theham-brand-film-16x9.mp4` | 1920×1080 · 홈페이지 / 유튜브 |
| `theham-brand-film-9x16.mp4` | 1080×1920 · 릴스 / 쇼츠 / 카톡 공유 |
| `poster-*.jpg` | 썸네일 (엔딩 카드) |

## 구성 (96 BPM, 1박 = 0.625초)
- 0:00 훅: 멀티탭 스파크 "탁" (CG)
- 0:02.5 오프닝: 실사 배경 4컷 위로 박자마다 한 단어씩 — 사고는 예고 없이 옵니다 / 불이 나고, 연기가 번지고 / 무엇이, 얼마나 손상됐는지 / 설명할 근거가 필요합니다
- 0:12.5 빌드업: 보이는 피해 너머까지. → 1박 무음
- 0:15 드롭 A: 한 박자에 한 단어 + 실사 배경 (불·연기·그을음·소방수 → 현장·측정·도면·약관 → 누락·근거·산정·설명 → 복구·일상·제자리·회복)
- 0:25 드롭 B: **최신 실제 페이지**(홈 · 유승민 대표 · 이도경 이사 선임권)를 폰 안에서 스크롤·탭
- 0:35 엔딩: 빠진 것을, 더합니다. → 로고 → 상호·태그라인 → 연락처 → 고지 문구 → 불씨

표현 기준(최신 페이지 문구 기준): 수임료 0원은 **선임권 한정**(보험회사 동의 등 요건 충족 시 보험회사가 손해사정 보수 부담)으로만 표기. 엔딩에 "보장 여부와 손해액은 보험계약 및 사고 내용에 따라 달라집니다." 고지.

## 다시 만들기
```bash
cd promo
npm install            # playwright, Pretendard, Noto Sans/Serif KR
pip install numpy scipy
./build.sh             # 음악 → 실사 클립 → 최신 페이지 → 16:9 / 9:16 렌더 → 합치기 → 포스터
```
- 박자표: `src/timeline.json` · 화면 연출: `src/film.js`, `src/film.html`
- 실사 클립: `src/footage.json` (Mixkit 클립 번호·시작 초·배속) → `src/footage.py`
- 폰 화면 페이지: `src/pages.py` (theham-consult.pages.dev 에서 최신본을 받음)
- CG 장면(훅 멀티탭, 빌드업 손전등, 누락 견적서): `src/scenes-gl.js`, `src/scenes-2d.js` — 셰이더만 확인: `node src/render.mjs --page gltest.html --q key=strip --preview 0.7`
- 음악: `src/music.py` (코드로 직접 합성 — 샘플·저작권 음원 없음)
- 특정 시점만 미리보기: `node src/render.mjs --fmt h --preview 16.3,31.8`

실사 클립: [Mixkit](https://mixkit.co) 무료 라이선스(상업 이용 가능·출처 표기 불필요). 원본 클립은 저장소에 넣지 않고 빌드 때 내려받음(`footage/`는 git 제외).
서체: Pretendard (SIL OFL), Noto Sans/Serif KR (SIL OFL).
