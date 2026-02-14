# 부동산 매물 관리 시스템 (Real Estate MVP)

Discord 봇을 통해 자연어로 부동산 매물을 검색/조회/등록/수정/삭제할 수 있는 시스템.

## 아키텍처

```
Discord 사용자 → Discord Bot → Claude API → MCP Server → PostgreSQL
```

## 기술 스택

- Python 3.11+
- FastMCP (MCP 서버)
- asyncpg (PostgreSQL 비동기 드라이버)
- discord.py (Discord 봇)
- Anthropic Claude API (자연어 처리)

## 프로젝트 구조

```
real-estate-mvp/
├── mcp_server/           # FastMCP 서버
│   ├── server.py         # Tools 7개 + Resources 3개
│   ├── db.py             # asyncpg 커넥션 풀
│   └── models.py         # Pydantic 모델
├── discord_bot/          # Discord 봇
│   ├── main.py           # 봇 엔트리포인트
│   ├── claude_client.py  # Claude API + MCP 브릿지
│   └── formatters.py     # 메시지 포맷팅
├── sql/                  # DDL 스크립트
│   ├── schema.sql        # 테이블, 인덱스
│   └── triggers.sql      # 트리거, 함수
├── tests/                # 테스트 코드
├── .env.template         # 환경변수 템플릿
├── SETUP_REQUIRED.md     # 설정 체크리스트
└── requirements.txt      # Python 의존성
```

## 설정

`SETUP_REQUIRED.md` 참조.

## MCP Tools (7개)

| Tool | 설명 |
|------|------|
| `search_properties` | 조건별 매물 검색 |
| `get_property_detail` | 매물 상세 조회 (변경이력 포함) |
| `create_property` | 매물 등록 |
| `update_property` | 매물 수정 |
| `delete_property` | 매물 삭제 (soft delete) |
| `get_property_statistics` | 매물 통계 |
| `compare_properties` | 매물 비교 (2~5개) |
