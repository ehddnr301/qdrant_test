# read_demo.py
"""
Qdrant 벡터 데이터베이스 사용 예제
- 하나의 질문으로 catalog, glossary, sql_history를 동시에 검색
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import OpenAI
import os
import time

from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# 클라이언트 초기화
# =============================================================================
qc = QdrantClient(url="http://localhost:6333")

# OpenAI 클라이언트 초기화 (API 키는 환경변수 OPENAI_API_KEY에서 가져옴)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 임베딩 함수
def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """OpenAI API를 사용하여 텍스트를 벡터로 변환"""
    response = openai_client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


# =============================================================================
# 하나의 질문으로 모든 컬렉션 검색
# =============================================================================
print("=" * 80)
print("통합 검색 예제: 하나의 질문으로 관련 정보 검색")
print("=" * 80)
print()

# 검색할 질문 (직급별 평균 연봉 조회 관련)
# - GLOSSARY: 직급, 연봉 용어 정보
# - CATALOG: employees 테이블의 title, salary 컬럼 정보
# - SQL_HISTORY: 직급별 평균 연봉 쿼리 예제
query = "직급별 평균 연봉 조회 방법"
print(f"검색 질문: '{query}'")
print()

# 질문을 벡터로 변환
query_vector = get_embedding(query)

# 전체 검색 시간 측정
total_start = time.time()

# =============================================================================
# (1) Glossary 검색 - 용어 및 정의
# =============================================================================
print("=" * 80)
print("[1] Glossary 검색 (용어 및 정의)")
print("=" * 80)

start_time = time.time()
glossary_results = qc.search(
    collection_name="hr_glossary",
    query_vector=query_vector,
    limit=5,
    score_threshold=0.3,
    query_filter=Filter(
        must=[FieldCondition(key="type", match=MatchValue(value="glossary"))]
    ),
)
glossary_time = (time.time() - start_time) * 1000

print(f"검색 시간: {glossary_time:.2f}ms")
print(f"결과: {len(glossary_results)}건")
print()

for idx, r in enumerate(glossary_results, 1):
    score_bar = "█" * int(r.score * 20)
    description = r.payload.get("description", "N/A") if r.payload else "N/A"
    if description != "N/A" and len(description) > 80:
        description = description[:80] + "..."

    print(f"  [{idx}] 점수: {r.score:.4f} {score_bar}")
    print(f"      ID: {r.id}")
    print(f"      제목: {r.payload.get('title', 'N/A') if r.payload else 'N/A'}")
    print(f"      설명: {description}")
    print()

print()

# =============================================================================
# (2) Catalog 검색 - 테이블 및 컬럼 정보
# =============================================================================
print("=" * 80)
print("[2] Catalog 검색 (테이블 및 컬럼 정보)")
print("=" * 80)

start_time = time.time()
catalog_results = qc.search(
    collection_name="hr_catalog",
    query_vector=query_vector,
    limit=5,
)
catalog_time = (time.time() - start_time) * 1000

print(f"검색 시간: {catalog_time:.2f}ms")
print(f"결과: {len(catalog_results)}건")
print()

for idx, r in enumerate(catalog_results, 1):
    score_bar = "█" * int(r.score * 20)
    print(f"  [{idx}] 점수: {r.score:.4f} {score_bar}")
    print(f"      ID: {r.id}")
    if r.payload:
        table_name = r.payload.get("table", "N/A")
        description = r.payload.get("description", "N/A")
        print(f"      테이블: {table_name}")
        if description != "N/A":
            print(f"      설명: {description}")

        # 컬럼 정보 전체 출력 (temp.py처럼)
        columns = r.payload.get("columns", [])
        if columns:
            print(f"      컬럼:")
            for col in columns:
                col_name = col.get("name", "N/A")
                col_desc = col.get("description", "")
                col_dtype = col.get("dtype", "N/A")
                print(f"        - {col_name} ({col_dtype}): {col_desc}")
    print()

print()

# =============================================================================
# (3) SQL History 검색 - 관련 SQL 쿼리 예제
# =============================================================================
print("=" * 80)
print("[3] SQL History 검색 (관련 SQL 쿼리 예제)")
print("=" * 80)

start_time = time.time()
sql_results = qc.search(
    collection_name="hr_sql_history",
    query_vector=query_vector,
    limit=5,
    score_threshold=0.1,
    query_filter=Filter(
        must=[FieldCondition(key="type", match=MatchValue(value="history"))]
    ),
)
sql_time = (time.time() - start_time) * 1000

print(f"검색 시간: {sql_time:.2f}ms")
print(f"결과: {len(sql_results)}건")
print()

for idx, r in enumerate(sql_results, 1):
    score_bar = "█" * int(r.score * 20)
    print(f"  [{idx}] 점수: {r.score:.4f} {score_bar}")
    print(f"      ID: {r.id}")
    if r.payload:
        print(f"      제목: {r.payload.get('title', 'N/A')}")
        description = r.payload.get("description", "N/A")
        if description != "N/A" and len(description) > 80:
            description = description[:80] + "..."
        print(f"      설명: {description}")
        if r.payload.get("sql"):
            query_preview = r.payload.get("sql", "")
            if len(query_preview) > 100:
                query_preview = query_preview[:100] + "..."
            print(f"      쿼리: {query_preview}")
    print()

print()

# =============================================================================
# 검색 요약
# =============================================================================
total_time = (time.time() - total_start) * 1000

print("=" * 80)
print("검색 요약")
print("=" * 80)
print(f"질문: '{query}'")
print(f"총 검색 시간: {total_time:.2f}ms")
print(f"  - Glossary: {glossary_time:.2f}ms ({len(glossary_results)}건)")
print(f"  - Catalog: {catalog_time:.2f}ms ({len(catalog_results)}건)")
print(f"  - SQL History: {sql_time:.2f}ms ({len(sql_results)}건)")
print()
