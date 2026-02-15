# ==============================================================================
# Stage 1: Builder - 의존성 설치 전용
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# 빌드 도구 설치 (컴파일 필요한 패키지 대비)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 의존성 먼저 복사 -> 캐시 레이어 활용
COPY pyproject.toml .

# wheel로 빌드하여 런타임 스테이지에서 빠르게 설치
RUN pip install --no-cache-dir --prefix=/install .

# ==============================================================================
# Stage 2: Runtime - 최소한의 런타임 이미지
# ==============================================================================
FROM python:3.12-slim AS runtime

# 런타임에 필요한 최소 라이브러리만 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# 비루트 사용자 생성 (보안)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# builder 스테이지에서 설치된 패키지 복사
COPY --from=builder /install /usr/local

# 앱 소스 복사
COPY . .

# 소유권 변경
RUN chown -R appuser:appuser /app

# 비루트 사용자로 전환
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크: /health 엔드포인트 30초 간격 확인
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 운영용 uvicorn 실행 옵션
# --workers: CPU 코어 수에 맞춰 조정 (기본 2, 환경변수로 오버라이드 가능)
# --timeout-keep-alive: 로드밸런서 뒤에서 keep-alive 타임아웃
# --access-log: 운영 환경 접근 로그 활성화
# --limit-max-requests: 메모리 릭 방지를 위한 워커 재시작 주기
ENV UVICORN_WORKERS=2
ENV UVICORN_TIMEOUT_KEEP_ALIVE=65
ENV UVICORN_LIMIT_MAX_REQUESTS=10000

CMD ["sh", "-c", \
    "uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers ${UVICORN_WORKERS} \
        --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE} \
        --limit-max-requests ${UVICORN_LIMIT_MAX_REQUESTS} \
        --access-log \
        --proxy-headers \
        --forwarded-allow-ips '*'"]
