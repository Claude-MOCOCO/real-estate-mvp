# 부동산 개인비서 MVP - 운영 문서

> 최종 업데이트: 2026-02-15
> 버전: 0.1.0

---

## 목차

1. [서비스 개요](#1-서비스-개요)
2. [환경 설정](#2-환경-설정)
3. [시작/종료/재시작 절차](#3-시작종료재시작-절차)
4. [API 명세](#4-api-명세)
5. [장애 대응 가이드](#5-장애-대응-가이드)
6. [보안 체크리스트](#6-보안-체크리스트)

---

## 1. 서비스 개요

### 시스템 아키텍처

```
[카카오톡 사용자]
       |
       v
[카카오 i 오픈빌더] ──── 스킬 요청 (POST /kakao/skill)
       |                          |
       |                 +-----------------+
       |                 |   FastAPI 서버   |
       |                 |  (uvicorn)       |
       |                 +-----------------+
       |                  |       |       |
       |          --------+       |       +--------
       |          |               |               |
       v          v               v               v
  [콜백 응답]  [PostgreSQL]  [OpenAI API]  [Properties API]
               (asyncpg)    (GPT-4o-mini)  (내부 CRUD)
```

**처리 흐름:**

1. 카카오 챗봇이 사용자 발화를 `/kakao/skill` 엔드포인트로 전달
2. `callbackUrl`이 있으면 즉시 대기 메시지 반환 후, 백그라운드에서 비동기 처리
3. `callbackUrl`이 없으면 직접 응답 (카카오 5초 제한 내)
4. OpenAI GPT-4o-mini가 자연어를 구조화된 매물 정보(ParseResult)로 변환
5. 의도(intent)에 따라 매물 등록/검색/삭제 또는 메모 저장 수행
6. 결과를 카카오 챗봇 응답 포맷(v2.0)으로 반환

### 아키텍처 패턴

헥사고날 아키텍처(포트앤어댑터) 적용:

```
app/
├── domain/          # 도메인 계층 — 엔티티, 값 객체, 포트(인터페이스)
├── application/     # 유스케이스 계층 — AssistantUseCase
├── adapters/        # 어댑터 계층 — SQLAlchemy, OpenAI, httpx 구현체
├── services/        # 하위호환 래퍼 (기존 import 경로 유지)
├── schemas/         # Pydantic 요청/응답 스키마
├── models/          # SQLAlchemy ORM 모델
├── api/             # FastAPI 라우터
└── core/            # 설정, DB, 인증, 미들웨어, 로깅
```

### 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | >= 3.11 (개발 환경 3.12) |
| 웹 프레임워크 | FastAPI | >= 0.115 |
| ASGI 서버 | uvicorn[standard] | >= 0.30 |
| ORM | SQLAlchemy (async) | >= 2.0 |
| DB 드라이버 | asyncpg | >= 0.30 |
| DB | PostgreSQL | 16 (Docker Alpine) |
| 마이그레이션 | Alembic | >= 1.14 |
| 검증/설정 | Pydantic / pydantic-settings | >= 2.0 |
| HTTP 클라이언트 | httpx | >= 0.28 |
| AI 파싱 | OpenAI (GPT-4o-mini) | >= 1.0 |
| 재시도 | tenacity | >= 8.0 |
| 환경변수 | python-dotenv | >= 1.0 |
| 테스트 | pytest + pytest-asyncio + pytest-httpx | dev 의존성 |

### 주요 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 헬스체크 (DB 연결 상태 포함) |
| `POST` | `/kakao/skill` | 카카오 챗봇 스킬 서버 |
| `GET` | `/api/properties/{agent_id}` | 매물 목록 조회 |
| `POST` | `/api/properties/{agent_id}` | 매물 생성 |
| `GET` | `/api/properties/{agent_id}/{property_id}` | 매물 단건 조회 |
| `PATCH` | `/api/properties/{agent_id}/{property_id}` | 매물 수정 |
| `DELETE` | `/api/properties/{agent_id}/{property_id}` | 매물 삭제 |

### DB 테이블 구조

| 테이블 | 설명 |
|--------|------|
| `agents` | 공인중개사(사용자). `kakao_user_id`로 식별 |
| `properties` | 매물 정보. 정형 컬럼 + JSONB(`extra`) 하이브리드 구조 |
| `memos` | 파싱 실패 시 원문 임시 저장용 메모 |

---

## 2. 환경 설정

### 환경변수 전체 목록

`.env.template` 파일을 `.env`로 복사한 후 실제 값을 입력한다.

| 변수명 | 필수 여부 | 기본값 | 설명 |
|--------|-----------|--------|------|
| `DATABASE_URL` | O | `postgresql+asyncpg://mcp_user:password@localhost:5432/real_estate` | PostgreSQL 접속 URL (asyncpg 드라이버) |
| `OPENAI_API_KEY` | production 필수 | (빈 문자열) | OpenAI API 키. 미설정 시 AI 파싱 기능 비활성화 |
| `OPENAI_MODEL` | X | `gpt-4o-mini` | 사용할 OpenAI 모델명 (코드 내 Settings 기본값) |
| `KAKAO_BOT_ID` | X | (빈 문자열) | 카카오 봇 ID (OBT 승인 후 입력) |
| `KAKAO_SKILL_SECRET` | X | (빈 문자열) | 카카오 스킬 시크릿. 미설정 시 시크릿 검증 건너뜀 |
| `ENVIRONMENT` | X | `development` | 실행 환경. `development` / `staging` / `production` |
| `LOG_LEVEL` | X | `INFO` | 로그 레벨. `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `API_KEY` | X | (빈 문자열) | Properties API 인증용 키. 미설정 시 인증 없이 동작 (개발 모드) |
| `CORS_ORIGINS` | X | `*` | CORS 허용 오리진 (콤마 구분). production에서는 `*` 사용 불가 |

### Docker 전용 환경변수 (Dockerfile 내 기본값)

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `UVICORN_WORKERS` | `2` | uvicorn 워커 수 (CPU 코어 수에 맞춰 조정) |
| `UVICORN_TIMEOUT_KEEP_ALIVE` | `65` | Keep-alive 타임아웃 (초). 로드밸런서 뒤에서 사용 |
| `UVICORN_LIMIT_MAX_REQUESTS` | `10000` | 워커당 최대 요청 수 (메모리 릭 방지용 재시작 주기) |

### 개발 환경 vs 운영 환경 차이

| 항목 | development | production |
|------|------------|------------|
| `OPENAI_API_KEY` | 선택 (미설정 시 경고만) | **필수** (미설정 시 서버 기동 실패) |
| `CORS_ORIGINS` | `*` 허용 | `*` **금지** (명시적 도메인 필수, 위반 시 기동 실패) |
| `API_KEY` | 미설정 시 인증 없이 통과 | 반드시 설정 권장 |
| `KAKAO_SKILL_SECRET` | 미설정 시 검증 건너뜀 | 반드시 설정 권장 |
| 로그 포맷 | 텍스트 (`%(asctime)s [%(levelname)s] %(name)s: %(message)s`) | **JSON** (`{"timestamp", "level", "logger", "message"}`) |
| DB 커넥션 풀 | pool_size=5, max_overflow=10 | 동일 (필요 시 코드 수정) |

---

## 3. 시작/종료/재시작 절차

### 3-1. 로컬 개발 환경 실행

**사전 요구사항:**
- Python 3.12+
- PostgreSQL 16+ 실행 중
- `.env` 파일 설정 완료

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2. 의존성 설치
pip install -e ".[dev]"

# 3. 환경변수 설정
cp .env.template .env
# .env 파일 편집하여 실제 값 입력

# 4. DB 마이그레이션
alembic upgrade head

# 5. 개발 서버 실행 (자동 리로드)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**헬스체크 확인:**
```bash
curl http://localhost:8000/health
# 정상 응답: {"status":"ok","database":"connected","version":"0.1.0",...}
```

### 3-2. Docker 기반 실행

```bash
# 1. 환경변수 파일 준비
cp .env.template .env
# .env 파일 편집

# 2. 전체 스택 기동 (DB + App)
docker compose up -d

# 3. 로그 확인
docker compose logs -f app

# 4. 헬스체크
curl http://localhost:8000/health
```

**Docker Compose 서비스 구성:**

| 서비스 | 이미지 | 포트 | 설명 |
|--------|--------|------|------|
| `db` | `postgres:16-alpine` | 5432 | PostgreSQL. 데이터는 `pgdata` 볼륨에 영구 저장 |
| `app` | 커스텀 빌드 (멀티스테이지) | 8000 | FastAPI 앱. `.env` 파일 자동 로드 |

**Docker 이미지 특성:**
- 멀티스테이지 빌드 (builder -> runtime)로 이미지 크기 최소화
- 비루트 사용자(`appuser`, UID 1000)로 실행 (보안)
- 헬스체크 내장: `/health` 엔드포인트 30초 간격 확인
- `--proxy-headers`와 `--forwarded-allow-ips '*'` 설정으로 리버스 프록시 대응

### 3-3. 프로세스 관리

**종료:**
```bash
# Docker 환경
docker compose down          # 컨테이너 종료 (데이터 유지)
docker compose down -v       # 컨테이너 + 볼륨 삭제 (데이터 삭제)

# 로컬 환경
# uvicorn 프로세스에 SIGINT(Ctrl+C) 또는 SIGTERM 전송
# lifespan 핸들러가 DB 커넥션 풀을 정리하고 종료
```

**재시작:**
```bash
# Docker 환경
docker compose restart app   # 앱만 재시작
docker compose up -d --build # 코드 변경 시 이미지 재빌드 후 재시작

# 로컬 환경 (--reload 모드에서는 파일 변경 시 자동 재시작)
```

**DB 마이그레이션 (스키마 변경 시):**
```bash
# 마이그레이션 파일 자동 생성
alembic revision --autogenerate -m "변경 내용 설명"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백 (1단계)
alembic downgrade -1
```

---

## 4. API 명세

### 4-1. 카카오 스킬 API

**`POST /kakao/skill`**

카카오 i 오픈빌더 스킬 서버 엔드포인트. 카카오 챗봇으로부터 사용자 발화를 수신하고 처리 결과를 반환한다.

**인증:** `X-Kakao-Skill-Secret` 헤더 (KAKAO_SKILL_SECRET 설정 시)

**요청 본문 (카카오 표준 포맷):**
```json
{
  "intent": {},
  "userRequest": {
    "timezone": "Asia/Seoul",
    "block": {},
    "utterance": "강남구 역삼동 30평 전세 3억 등록해줘",
    "lang": "ko",
    "params": {
      "plusfriendUserKey": "사용자_고유키"
    }
  },
  "bot": { "id": "", "name": "" },
  "action": { "id": "", "name": "", "params": {}, "detailParams": {}, "clientExtra": {} },
  "callbackUrl": "https://callback.kakao.com/..."
}
```

**응답 분기:**

| 조건 | 동작 | 응답 |
|------|------|------|
| `callbackUrl` 있음 | 즉시 대기 메시지 반환 + 백그라운드 비동기 처리 (25초 타임아웃) | `useCallback: true` + 대기 메시지 |
| `callbackUrl` 없음 | 직접 처리 후 응답 (카카오 5초 제한 내) | 처리 결과 텍스트 |
| 빈 발화 | 즉시 안내 메시지 | "말씀해주세요!" |
| Rate limit 초과 | 즉시 안내 메시지 | "요청이 너무 빨라요." |
| 잘못된 사용자 키 | 즉시 안내 메시지 | "사용자 인증에 실패했어요." |

**응답 본문 (카카오 v2.0 포맷):**
```json
{
  "version": "2.0",
  "useCallback": true,
  "template": {
    "outputs": [
      {
        "simpleText": {
          "text": "매물 등록 중이에요... 잠시만요!"
        }
      }
    ]
  }
}
```

**Rate Limiting:**
- 동일 사용자 기준 초당 최대 2회
- 인메모리 방식 (서버 재시작 시 초기화)
- 1000명 초과 시 오래된 사용자 데이터 자동 정리

**지원 의도(intent):**

| intent | 트리거 키워드 | 동작 |
|--------|-------------|------|
| `register` | 등록, 추가, 넣어, 올려 | 매물 등록 (confidence >= 0.3 필요) |
| `search` | 찾아, 검색, 조회, 있어 | 매물 검색 (조건 없으면 전체 목록) |
| `delete` | 삭제, 지워, 빼 | 매물 소프트 삭제 |
| `update` | 수정, 바꿔, 변경 | MVP에서는 안내만 (삭제 후 재등록 권유) |
| `list_memo` | 메모, 메모 보여줘 | 저장된 메모 목록 조회 |
| `unknown` | (판단 불가) | 메모로 자동 저장 + 사용 안내 |

**콜백 URL 검증:**
- scheme: `http` 또는 `https`만 허용
- 최대 길이: 2048자
- SSRF 방지: `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`, `10.*`, `192.168.*`, `172.*` 차단
- 유효하지 않은 URL은 무시하고 직접 응답 모드로 전환

### 4-2. Properties CRUD API

내부 매물 관리 API. 개발/디버깅 용도로 설계되었으며, 모든 엔드포인트에 `verify_api_key` 의존성이 적용된다.

**인증:** `X-API-Key` 헤더 (API_KEY 환경변수 설정 시)

---

#### `GET /api/properties/{agent_id}`

매물 목록 조회.

**경로 파라미터:**
- `agent_id` (UUID, 필수): 공인중개사 ID

**쿼리 파라미터:**

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `transaction_type` | string | null | - | 거래 유형 필터 (매매/전세/월세) |
| `address_gugun` | string | null | - | 구/군 필터 |
| `limit` | int | 50 | 1~200 | 페이지 크기 |
| `offset` | int | 0 | >= 0 | 시작 위치 |

**응답:** `PropertyResponse[]` (200 OK)

---

#### `POST /api/properties/{agent_id}`

매물 생성.

**경로 파라미터:**
- `agent_id` (UUID, 필수): 공인중개사 ID

**요청 본문 (PropertyCreate):**
```json
{
  "transaction_type": "전세",
  "price_main": 300000000,
  "price_monthly": null,
  "area_pyeong": 30.0,
  "address_sido": "서울",
  "address_gugun": "강남구",
  "address_dong": "역삼동",
  "building_name": "래미안",
  "extra": {},
  "raw_input": "원문 텍스트"
}
```

**응답:** `PropertyResponse` (201 Created)

---

#### `GET /api/properties/{agent_id}/{property_id}`

매물 단건 조회.

**응답:** `PropertyResponse` (200 OK) 또는 404

---

#### `PATCH /api/properties/{agent_id}/{property_id}`

매물 수정 (부분 업데이트).

**요청 본문 (PropertyUpdate):** PropertyCreate와 동일한 필드 (raw_input 제외), 미전송 필드는 변경하지 않음

**응답:** `PropertyResponse` (200 OK) 또는 404

---

#### `DELETE /api/properties/{agent_id}/{property_id}`

매물 삭제 (소프트 삭제 - status를 `deleted`로 변경).

**응답:** 204 No Content 또는 404

---

#### PropertyResponse 스키마

```json
{
  "id": "uuid",
  "agent_id": "uuid",
  "transaction_type": "전세",
  "price_main": 300000000,
  "price_monthly": null,
  "area_pyeong": 30.0,
  "address_sido": "서울",
  "address_gugun": "강남구",
  "address_dong": "역삼동",
  "building_name": "래미안",
  "extra": {},
  "raw_input": "원문 텍스트",
  "status": "active",
  "created_at": "2026-02-15T12:00:00+09:00",
  "updated_at": "2026-02-15T12:00:00+09:00"
}
```

**PropertyStatus 열거형:** `active` / `sold` / `deleted`

### 4-3. 헬스체크 API

**`GET /health`**

서버 상태 및 DB 연결 확인.

**인증:** 없음

**정상 응답 (200):**
```json
{
  "status": "ok",
  "database": "connected",
  "version": "0.1.0",
  "environment": "development",
  "uptime_seconds": 3600
}
```

**DB 연결 실패 응답 (503):**
```json
{
  "status": "degraded",
  "database": "disconnected",
  "version": "0.1.0",
  "environment": "development",
  "uptime_seconds": 3600
}
```

### 4-4. 인증 방식 정리

| 엔드포인트 | 인증 방식 | 헤더 | 미설정 시 동작 |
|-----------|----------|------|--------------|
| `/kakao/skill` | 카카오 스킬 시크릿 | `X-Kakao-Skill-Secret` | 검증 건너뜀 (개발 모드) |
| `/api/properties/*` | API 키 | `X-API-Key` | 인증 없이 통과 (개발 모드) |
| `/health` | 없음 | - | - |

---

## 5. 장애 대응 가이드

### 5-1. DB 연결 실패 시

**증상:**
- `/health` 응답이 503 + `"database": "disconnected"`
- 카카오 스킬 요청 시 "일시적인 오류" 응답
- 로그에 `Health check DB 연결 실패` 또는 `DB 세션 생성 실패` 메시지

**확인 절차:**
```bash
# 1. DB 프로세스 상태 확인
docker compose ps db
# 또는
pg_isready -h localhost -p 5432

# 2. DB 연결 테스트
psql postgresql://mcp_user:password@localhost:5432/real_estate -c "SELECT 1"

# 3. 앱 로그 확인
docker compose logs --tail=50 app | grep -i "db\|database\|connection"
```

**조치:**
1. PostgreSQL 서비스 재시작: `docker compose restart db`
2. `DATABASE_URL` 환경변수 확인 (호스트, 포트, 인증정보)
3. DB 커넥션 풀 소진 시 앱 재시작: `docker compose restart app`
4. 커넥션 풀 설정 확인 (`app/core/database.py`):
   - `pool_size=5`: 기본 커넥션 수
   - `max_overflow=10`: 최대 추가 커넥션 수
   - `pool_timeout=30`: 커넥션 대기 타임아웃 (초)
   - `pool_recycle=1800`: 커넥션 재활용 주기 (30분)

### 5-2. OpenAI API 오류 시

**증상:**
- 매물 등록/검색 시 "잠시 오류가 발생했어요. 다시 시도해주세요." 응답
- 로그에 `AI 파싱 오류` 메시지

**자동 복구 메커니즘:**
- tenacity 라이브러리로 일시적 오류 자동 재시도 (최대 3회, 지수 백오프)
- 재시도 대상 오류: `RateLimitError`, `APIConnectionError`, `APITimeoutError`
- OpenAI API 호출 타임아웃: 10초

**확인 절차:**
```bash
# 1. OpenAI API 키 유효성 확인
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | head -20

# 2. 앱 로그에서 오류 유형 확인
docker compose logs --tail=100 app | grep -i "openai\|AI 파싱"
```

**조치:**
1. `RateLimitError`: OpenAI 사용량 대시보드 확인, 필요 시 플랜 업그레이드
2. `APIConnectionError`: 서버의 외부 네트워크 연결 확인
3. `APITimeoutError`: OpenAI 서비스 상태 페이지(https://status.openai.com) 확인
4. API 키 만료/비활성화: 새 키 발급 후 `OPENAI_API_KEY` 환경변수 갱신 및 앱 재시작

### 5-3. 카카오 콜백 타임아웃 시

**증상:**
- 사용자에게 대기 메시지만 표시되고 최종 응답이 오지 않음
- 로그에 `백그라운드 처리 타임아웃(25초)` 메시지

**메커니즘:**
- 콜백 모드에서 백그라운드 처리에 25초 타임아웃 적용 (`asyncio.wait_for`)
- 타임아웃 발생 시 에러 메시지를 콜백 URL로 전송 시도
- 콜백 전송 자체의 httpx 타임아웃: 10초 (정상 콜백), 5초 (에러 콜백)

**확인 절차:**
```bash
# 타임아웃 로그 확인
docker compose logs --tail=200 app | grep -i "타임아웃\|timeout\|콜백"
```

**조치:**
1. OpenAI API 응답 지연이 원인인 경우 -> 5-2 참조
2. DB 쿼리 지연이 원인인 경우 -> 5-1 참조, 인덱스 확인
3. 반복 발생 시 `OPENAI_MODEL`을 더 빠른 모델로 변경 검토

### 5-4. 로그 확인 방법

**로그 출력 위치:** stdout (표준 출력)

**로그 포맷:**
- 개발 환경: `2026-02-15 12:00:00,000 [INFO] app.api.kakao: 스킬 요청: user=xxx, utterance=...`
- 운영 환경 (JSON): `{"timestamp":"2026-02-15 12:00:00,000","level":"INFO","logger":"app.api.kakao","message":"스킬 요청: ..."}`

**로그 레벨 조정:**
```bash
# .env 파일에서 변경
LOG_LEVEL=DEBUG  # 상세 로그 (개발 시)
LOG_LEVEL=WARNING  # 경고 이상만 (운영 안정화 후)
```

**외부 라이브러리 로그:**
- `httpx`, `httpcore`, `sqlalchemy.engine`: WARNING 레벨로 고정 (노이즈 방지)

**주요 로그 키워드:**

| 키워드 | 위치 | 의미 |
|--------|------|------|
| `스킬 요청` | kakao.py | 카카오 스킬 수신 |
| `파싱 결과` | assistant.py | AI 파싱 완료 |
| `콜백 전송 완료` | kakao.py | 비동기 콜백 성공 |
| `콜백 처리 실패` | kakao.py | 비동기 콜백 실패 |
| `Rate limit 초과` | kakao.py | 사용자별 요청 제한 초과 |
| `AI 파싱 오류` | parser.py | OpenAI API 호출 실패 |
| `매물 등록(파싱)` | property_service.py | 매물 DB 저장 성공 |
| `처리되지 않은 예외` | main.py | 글로벌 예외 핸들러 포착 |

**Request ID 추적:**
- 모든 요청에 `X-Request-ID` 헤더가 부여됨 (기존 헤더가 없으면 UUID 자동 생성)
- 응답 헤더에도 동일 ID 포함
- 로그에 `request_id` 필드로 기록 가능 (JSON 포맷 시)

### 5-5. Rate Limiting 관련 이슈

**현재 구현:**
- 인메모리 딕셔너리 기반 (서버 재시작 시 초기화)
- 동일 `plusfriendUserKey` 기준 1초당 최대 2회
- 1000명 초과 시 오래된 사용자 자동 정리 (윈도우 x 10 이상 경과)

**알려진 제한:**
- 멀티 워커 환경에서는 워커별 독립 rate limit (공유 안 됨)
- 서버 재시작 시 rate limit 카운터 초기화
- 분산 환경에서는 Redis 기반 rate limiter로 교체 필요

**Rate limit 관련 로그:**
```
WARNING  Rate limit 초과: user=xxx
```

---

## 6. 보안 체크리스트

### 6-1. 운영 환경 필수 설정 항목

운영(`ENVIRONMENT=production`) 배포 전 반드시 확인해야 할 항목:

- [ ] `OPENAI_API_KEY` 설정 완료 (미설정 시 서버 기동 실패)
- [ ] `CORS_ORIGINS`에 명시적 도메인 설정 (`*` 사용 시 서버 기동 실패)
- [ ] `API_KEY` 설정 (Properties API 보호)
- [ ] `KAKAO_SKILL_SECRET` 설정 (카카오 스킬 엔드포인트 보호)
- [ ] `DATABASE_URL`에 운영 DB 인증정보 적용 (기본값 password 변경)
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인 (포함됨)
- [ ] Docker 이미지가 비루트 사용자(`appuser`)로 실행되는지 확인

### 6-2. API 키 관리

**Properties API (`X-API-Key`):**
- `API_KEY` 환경변수로 설정
- 미설정 시 모든 요청이 인증 없이 통과 (개발 전용)
- 운영 환경에서는 충분히 긴 랜덤 문자열 사용 권장

**카카오 스킬 시크릿 (`X-Kakao-Skill-Secret`):**
- `KAKAO_SKILL_SECRET` 환경변수로 설정
- 카카오 i 오픈빌더의 스킬 설정에서 발급받은 시크릿 키
- 미설정 시 검증 건너뜀 (개발 전용)
- 검증 실패 시 로그에 요청자 IP 기록

**OpenAI API 키:**
- `OPENAI_API_KEY` 환경변수로 설정
- 절대 소스코드나 Git에 커밋하지 않을 것
- OpenAI 대시보드에서 주기적으로 키 로테이션 권장

### 6-3. CORS 설정

**코드 위치:** `app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # CORS_ORIGINS 환경변수
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**설정 규칙:**
- `CORS_ORIGINS` 환경변수에 콤마로 구분하여 오리진 목록 지정
- `ENVIRONMENT=production`에서 `*`를 설정하면 **서버가 기동되지 않음** (pydantic model_validator에서 차단)
- 예시: `CORS_ORIGINS=https://admin.example.com,https://app.example.com`

### 6-4. 기타 보안 사항

**입력값 검증:**
- 카카오 발화(`utterance`): 최대 1000자 제한 (Pydantic)
- 콜백 URL: scheme/host 검증 + SSRF 방지 (내부 네트워크 IP 차단)
- `plusfriendUserKey`: 빈 문자열/100자 초과 시 요청 거부
- 메모 내용: 최대 5000자 제한 (SQLAlchemy validates)
- Properties API 필드: Pydantic Field 제약 조건 적용 (max_length, ge, le 등)

**글로벌 예외 처리 (`app/main.py`):**
- `/kakao` 경로 요청에서 미처리 예외 발생 시, 내부 오류 상세를 숨기고 사용자 친화적 메시지 반환
- 기타 경로에서는 500 + `{"detail": "Internal server error"}` 반환 (내부 정보 비노출)

**소프트 삭제:**
- 매물 삭제 시 DB에서 물리적으로 제거하지 않고 `status`를 `deleted`로 변경
- 조회 시 `status=active`인 매물만 반환
