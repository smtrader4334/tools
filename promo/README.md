# 더함 브랜드 필름 (46초)

`theham-consult.html` 홈페이지 홍보 영상. 브랜드 한 줄: **빠진 것을, 더합니다.**

| 파일 | 용도 |
|---|---|
| `theham-brand-film-16x9.mp4` | 1920×1080 · 홈페이지 / 유튜브 |
| `theham-brand-film-9x16.mp4` | 1080×1920 · 릴스 / 쇼츠 / 카톡 공유 |
| `poster-*.jpg` | 썸네일 (엔딩 카드) |

## 구성 (120 BPM, 1박 = 0.5초)
- 0:00 훅: 천장 누수 → 대야에 "톡"
- 0:02 오프닝: 검은 화면 + 큰 글자, 박자마다 쾅
- 0:12 빌드업: "그럼, 누가 내 편에 서죠?" → 1박 무음
- 0:16 드롭 A: 한 박자에 한 단어 + 단어에 맞는 실사 배경 (불·물·그을음 … 당신 편)
- 0:24 드롭 B: **실제 홈페이지**를 폰 안에 띄워 스크롤·탭 (목업 없음)
- 0:36 엔딩: 빠진 것을, 더합니다. → 로고 → 상호·상담 연락처 → 물방울

## 다시 만들기
```bash
cd promo
npm install            # playwright, Pretendard, Noto Sans/Serif KR
pip install numpy scipy
./build.sh             # 음악 → 16:9 / 9:16 렌더 → 합치기 → 포스터
```
- 문구·타이밍: `src/timeline.json`(박자표), `src/film.js`(화면 연출)
- 드롭 A 실사 클립: `src/footage.json` (Mixkit 클립 번호·시작 초·배속) → `src/footage.py`가 내려받아 프레임 추출
- 훅·누락·당신 편 장면(및 실사가 없을 때 대체): `src/scenes-gl.js`(셰이더), `src/scenes-2d.js`(모션그래픽)
- 음악: `src/music.py` (코드로 직접 합성 — 샘플·저작권 음원 없음)
- 특정 시점만 미리보기: `node src/render.mjs --fmt h --preview 16.3,31.8`

실사 클립: [Mixkit](https://mixkit.co) 무료 라이선스(상업 이용 가능·출처 표기 불필요). 원본 클립은 저장소에 넣지 않고 빌드 때 내려받음(`footage/`는 git 제외).
서체: Pretendard (SIL OFL), Noto Sans/Serif KR (SIL OFL). 영상 속 금액(₩8,400,000 → ₩3,200,000)은 연출된 예시로 화면에 표기됨.
