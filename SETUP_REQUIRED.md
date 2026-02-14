# 회장님 처리 필요 항목

> 이 문서는 프로젝트 실행을 위해 회장님께서 직접 처리하셔야 할 항목들을 정리한 체크리스트입니다.

---

## 1. PostgreSQL 데이터베이스

- [ ] DB 생성 (이름: `real_estate` 또는 기존 atom.io DB 사용)
- [ ] DB 전용 유저 생성 (이름: `mcp_user`, 최소 권한)
  ```sql
  CREATE USER mcp_user WITH PASSWORD 'your_password';
  GRANT CONNECT ON DATABASE real_estate TO mcp_user;
  GRANT USAGE ON SCHEMA public TO mcp_user;
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO mcp_user;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mcp_user;
  ```
- [ ] 스키마 생성: `psql -d real_estate -f sql/schema.sql`
- [ ] 트리거 생성: `psql -d real_estate -f sql/triggers.sql`

## 2. 환경변수 (.env)

`.env.template`을 `.env`로 복사 후 실제 값 입력:

- [ ] `DISCORD_BOT_TOKEN` — Discord Developer Portal에서 발급
- [ ] `ANTHROPIC_API_KEY` — Anthropic 대시보드에서 발급
- [ ] `DATABASE_URL` — PostgreSQL 접속 URL
  - 형식: `postgresql://mcp_user:password@host:port/real_estate`

## 3. Discord 봇 설정

- [ ] [Discord Developer Portal](https://discord.com/developers/applications)에서 Application 생성
- [ ] Bot 탭 → Bot 생성 → TOKEN 복사
- [ ] Bot 탭 → Privileged Gateway Intents → Message Content Intent 활성화
- [ ] OAuth2 → URL Generator:
  - Scopes: `bot`
  - Bot Permissions: `Send Messages`, `Read Message History`, `Use Slash Commands`
- [ ] 생성된 초대 링크로 서버에 봇 추가

## 4. Python 환경

- [ ] Python 3.11+ 확인: `python --version`
- [ ] 가상환경 생성 (선택):
  ```bash
  cd ~/Desktop/cj/real-estate-mvp
  python -m venv venv
  source venv/bin/activate
  ```
- [ ] 의존성 설치:
  ```bash
  pip install -r requirements.txt
  ```

## 5. 실행

```bash
cd ~/Desktop/cj/real-estate-mvp

# MCP 서버 단독 테스트 (선택)
cd mcp_server && python server.py

# Discord 봇 실행
cd discord_bot && python main.py
```

---

## 결정 사항 메모

> BE코코가 프로젝트 생성 과정에서 내린 결정들 (회장님 확인용)

| # | 결정 사항 | 이유 |
|---|----------|------|
| 1 | 프로젝트 경로: `~/Desktop/cj/real-estate-mvp` | 회장님 지시 (`~/Desktop/cj` 하위) |
| 2 | **독립 git 레포** (atom.io와 분리) | 회장님 지시: atom.io 심볼릭 링크 불필요, 부동산 레포 독립 생성 |
| 3 | mococo-corps/repos에 심볼릭 링크 등록 | 통합 관리 편의성 |
| 4 | 설계서 코드를 실행 가능한 형태로 작성 | 설계서에 이미 완성된 코드가 있어 바로 실행 가능 수준으로 작성 |
| 5 | `pyproject.toml` + `requirements.txt` 이중 관리 | pyproject.toml은 프로젝트 메타데이터, requirements.txt는 빠른 설치용 |
| 6 | 프로덕션 브랜치: `main` | 독립 레포이므로 main 브랜치 사용 |
