"""
Course 6-1: 최종 프로젝트 - 프로덕션 준비 문서 검색 엔진
하이브리드 검색, 멀티벡터 재랭킹, 성능 평가를 포함한 완전한 문서 검색 시스템을 구축합니다.
"""

from qdrant_client import QdrantClient, models
from openai import OpenAI
import time
import random
import os

from dotenv import load_dotenv

load_dotenv()

# Docker로 실행한 Qdrant 서버에 연결
client = QdrantClient(url="http://localhost:6333")


# OpenAI 클라이언트 초기화
print("임베딩 모델 초기화 중...")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536  # text-embedding-3-small의 차원
print("✅ OpenAI 클라이언트 초기화 완료")


def get_embedding(text):
    """텍스트를 OpenAI 임베딩으로 변환"""
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


print("=" * 60)
print("프로덕션 준비 문서 검색 엔진 구축")
print("=" * 60)

# 1. 컬렉션 설계
print("\n1️⃣ 컬렉션 설계:")

collection_name = "docs_search"

client.create_collection(
    collection_name=collection_name,
    vectors_config={
        "dense": models.VectorParams(size=1536, distance=models.Distance.COSINE),
        "colbert": models.VectorParams(
            size=128,
            distance=models.Distance.COSINE,
            multivector_config=models.MultiVectorConfig(
                comparator=models.MultiVectorComparator.MAX_SIM
            ),
            hnsw_config=models.HnswConfigDiff(m=0),
        ),
    },
    sparse_vectors_config={"sparse": models.SparseVectorParams()},
)

print(f"✅ 컬렉션 '{collection_name}' 생성 완료")
print("  - Dense: 빠른 검색")
print("  - Sparse: 키워드 매칭")
print("  - ColBERT: 정밀 재랭킹")

# 2. 샘플 문서 데이터 (문서 구조 기반)
print("\n2️⃣ 샘플 문서 데이터 준비:")

documents = [
    {
        "id": 1,
        "page_title": "HNSW 설정 가이드",
        "section_title": "HNSW 파라미터",
        "section_url": "/docs/guides/configuration/#hnsw-parameters",
        "breadcrumbs": ["Guides", "Configuration", "HNSW Parameters"],
        "chunk_text": "HNSW 알고리즘의 m 파라미터는 각 노드의 최대 연결 수를 제어합니다. "
        "높은 m 값은 더 정확한 검색을 제공하지만 더 많은 메모리를 사용합니다. "
        "기본값은 16이며, 8-64 범위에서 조정할 수 있습니다.",
        "prev_section_text": "이전 섹션: 컬렉션 생성",
        "next_section_text": "다음 섹션: 양자화 설정",
        "tags": ["configuration", "performance", "hnsw"],
    },
    {
        "id": 2,
        "page_title": "양자화 가이드",
        "section_title": "메모리 절감",
        "section_url": "/docs/guides/quantization/#memory-reduction",
        "breadcrumbs": ["Guides", "Quantization", "Memory Reduction"],
        "chunk_text": "Scalar 양자화는 Float32를 Int8로 변환하여 4배의 메모리 절감을 제공합니다. "
        "정확도는 99% 이상을 유지하면서 검색 속도도 향상시킬 수 있습니다.",
        "prev_section_text": "이전 섹션: 양자화 소개",
        "next_section_text": "다음 섹션: Binary 양자화",
        "tags": ["quantization", "optimization", "memory"],
    },
    {
        "id": 3,
        "page_title": "하이브리드 검색",
        "section_title": "RRF 결합",
        "section_url": "/docs/concepts/hybrid-queries/#rrf-fusion",
        "breadcrumbs": ["Concepts", "Hybrid Queries", "RRF Fusion"],
        "chunk_text": "Reciprocal Rank Fusion은 여러 검색 결과를 순위 기반으로 결합합니다. "
        "각 검색 방법의 점수를 정규화할 필요 없이 순위만으로 결합할 수 있습니다.",
        "prev_section_text": "이전 섹션: 하이브리드 검색 소개",
        "next_section_text": "다음 섹션: DBSF",
        "tags": ["hybrid-search", "fusion", "rrf"],
    },
    {
        "id": 4,
        "page_title": "컬렉션 생성",
        "section_title": "복제 인수 설정",
        "section_url": "/docs/guides/distributed-deployment/#replication-factor",
        "breadcrumbs": ["Guides", "Distributed Deployment", "Replication Factor"],
        "chunk_text": "복제 인수는 각 샤드의 복제본 수를 결정합니다. "
        "높은 복제 인수는 가용성을 향상시키지만 더 많은 리소스를 사용합니다.",
        "prev_section_text": "이전 섹션: 샤딩",
        "next_section_text": "다음 섹션: 클러스터 설정",
        "tags": ["distributed", "replication", "deployment"],
    },
]

# 키워드 인덱스 매핑
keyword_to_index = {}
index_counter = 0
all_keywords = set()
for doc in documents:
    for tag in doc["tags"]:
        all_keywords.add(tag)
        if tag not in keyword_to_index:
            keyword_to_index[tag] = index_counter
            index_counter += 1

print(f"✅ {len(documents)}개 문서 섹션 준비 완료")
print(f"✅ {len(keyword_to_index)}개 키워드 인덱스 생성")

# 3. 문서 임베딩 및 업로드
print("\n3️⃣ 문서 임베딩 및 업로드:")

points = []
for doc in documents:
    # ===== 벡터(Vector): 검색을 위한 임베딩 =====
    # - chunk_text만 임베딩: 검색 매칭에 사용되는 텍스트
    # - 이 벡터로 "무엇을 찾을지" 결정 (유사도 계산)
    # - 다른 정보(page_title, section_title 등)는 벡터화하지 않음
    dense_vector = get_embedding(doc["chunk_text"])

    # Sparse 벡터 생성 (태그 기반)
    indices = []
    values = []
    for tag in doc["tags"]:
        if tag in keyword_to_index:
            indices.append(keyword_to_index[tag])
            values.append(1.0)

    sparse_vector = models.SparseVector(indices=indices, values=values)

    # ColBERT 멀티벡터 생성 (시뮬레이션)
    tokens = doc["chunk_text"].split()
    colbert_multivector = [
        [random.random() for _ in range(128)]
        for _ in range(min(len(tokens), 20))  # 최대 20개 토큰
    ]

    points.append(
        models.PointStruct(
            id=doc["id"],
            # ===== vector: 검색 매칭을 위한 벡터 =====
            # - chunk_text를 임베딩한 벡터들만 저장
            # - 검색 시 유사도 계산에 사용됨
            # - "어떤 문서를 찾을지" 결정
            vector={
                "dense": dense_vector,
                "sparse": sparse_vector,
                "colbert": colbert_multivector,
            },
            # ===== payload: 검색 결과 표시/필터링용 메타데이터 =====
            # - 벡터화하지 않고 원본 그대로 저장 (JSON 형태)
            # - 검색 결과로 반환될 때 이 정보들이 함께 나옴
            # - "찾은 문서를 어떻게 보여줄지" 결정
            # - 필터링, 그룹핑, 정렬 등에도 사용 가능
            payload={
                "page_title": doc["page_title"],  # 검색 결과에 표시
                "section_title": doc["section_title"],  # 검색 결과에 표시
                "section_url": doc["section_url"],  # 검색 결과에 표시
                "breadcrumbs": doc["breadcrumbs"],  # 검색 결과에 표시
                "chunk_text": doc["chunk_text"],  # 검색 결과 스니펫용
                "prev_section_text": doc["prev_section_text"],  # 컨텍스트용
                "next_section_text": doc["next_section_text"],  # 컨텍스트용
                "tags": doc["tags"],  # 필터링/태그 표시용
            },
        )
    )

client.upload_points(collection_name=collection_name, points=points)
print(f"✅ {len(points)}개 문서 벡터 업로드 완료")

# 4. 하이브리드 검색 파이프라인
print("\n" + "=" * 60)
print("하이브리드 검색 파이프라인")
print("=" * 60)


def hybrid_search(query, limit=5):
    """
    하이브리드 검색 파이프라인:
    1. Dense + Sparse 병렬 검색
    2. RRF로 결합
    3. ColBERT로 재랭킹
    """
    # 벡터 생성
    dense_query = get_embedding(query)

    # Sparse 벡터 생성 (간단한 키워드 추출)
    query_words = query.lower().split()
    query_indices = []
    for word in query_words:
        for keyword, idx in keyword_to_index.items():
            if word in keyword.lower():
                if idx not in query_indices:
                    query_indices.append(idx)

    query_sparse = models.SparseVector(
        indices=query_indices, values=[1.0] * len(query_indices)
    )

    # ColBERT 쿼리 멀티벡터 (시뮬레이션)
    colbert_query = [
        [random.random() for _ in range(128)]
        for _ in range(min(len(query.split()), 10))
    ]

    # 하이브리드 검색 실행
    results = client.query_points(
        collection_name=collection_name,
        prefetch=[
            models.Prefetch(query=dense_query, using="dense", limit=50),  # 후보 수
            models.Prefetch(query=query_sparse, using="sparse", limit=50),
        ],
        query=colbert_query,
        using="colbert",  # ColBERT 재랭킹
        limit=limit,
    )

    return results


# 5. 검색 테스트
print("\n4️⃣ 검색 테스트:")

test_queries = [
    "HNSW 파라미터 설정 방법",
    "메모리 절감을 위한 양자화",
    "하이브리드 검색에서 결과 결합",
    "복제 인수 설정",
]

for query in test_queries:
    print(f"\n검색: '{query}'")
    results = hybrid_search(query, limit=3)

    # 검색 결과: point.payload에서 모든 메타데이터에 접근 가능
    # - point.score: 벡터 유사도 점수 (chunk_text 임베딩 기반)
    # - point.payload: 저장된 모든 메타데이터 (page_title, section_title, URL 등)
    for i, point in enumerate(results.points, 1):
        print(f"  {i}. {point.payload['section_title']}")  # 페이로드에서 가져옴
        print(f"     URL: {point.payload['section_url']}")  # 페이로드에서 가져옴
        print(f"     점수: {point.score:.4f}")  # 벡터 유사도 점수
        print(f"     태그: {', '.join(point.payload['tags'])}")  # 페이로드에서 가져옴

# 6. 평가 프레임워크
print("\n" + "=" * 60)
print("평가 프레임워크")
print("=" * 60)

# Ground Truth 데이터
ground_truth = [
    {
        "query": "HNSW 파라미터 설정",
        "expected_urls": ["/docs/guides/configuration/#hnsw-parameters"],
        "query_type": "how-to",
    },
    {
        "query": "양자화 메모리 절감",
        "expected_urls": ["/docs/guides/quantization/#memory-reduction"],
        "query_type": "concept",
    },
    {
        "query": "RRF 결과 결합",
        "expected_urls": ["/docs/concepts/hybrid-queries/#rrf-fusion"],
        "query_type": "concept",
    },
    {
        "query": "복제 인수 설정",
        "expected_urls": ["/docs/guides/distributed-deployment/#replication-factor"],
        "query_type": "api-usage",
    },
]

print("\n5️⃣ 성능 평가 수행:")


def evaluate_search(ground_truth, k=10):
    """검색 성능 평가"""
    recall_scores = []
    mrr_scores = []
    latencies = []

    for gt in ground_truth:
        # 검색 실행 및 시간 측정
        start_time = time.time()
        results = hybrid_search(gt["query"], limit=k)
        latency = (time.time() - start_time) * 1000  # ms
        latencies.append(latency)

        # Recall@K 계산
        found = False
        for point in results.points:
            if point.payload["section_url"] in gt["expected_urls"]:
                found = True
                break
        recall_scores.append(1.0 if found else 0.0)

        # MRR 계산
        mrr = 0.0
        for rank, point in enumerate(results.points, 1):
            if point.payload["section_url"] in gt["expected_urls"]:
                mrr = 1.0 / rank
                break
        mrr_scores.append(mrr)

    # 평균 계산
    recall_at_k = sum(recall_scores) / len(recall_scores)
    mrr = sum(mrr_scores) / len(mrr_scores)
    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]

    return {
        "recall_at_k": recall_at_k,
        "mrr": mrr,
        "p50": p50,
        "p95": p95,
        "latencies": latencies,
    }


metrics = evaluate_search(ground_truth, k=10)

print("\n평가 결과:")
print(f"  Recall@10: {metrics['recall_at_k']:.2%}")
print(f"  MRR: {metrics['mrr']:.3f}")
print(f"  P50 지연시간: {metrics['p50']:.2f}ms")
print(f"  P95 지연시간: {metrics['p95']:.2f}ms")

# 7. 결과 포맷팅
print("\n" + "=" * 60)
print("결과 포맷팅")
print("=" * 60)


def format_search_results(query, results):
    """검색 결과를 사용자 친화적 형식으로 변환"""
    formatted = []
    for i, point in enumerate(results.points, 1):
        formatted.append(
            {
                "rank": i,
                "title": point.payload["section_title"],
                "page": point.payload["page_title"],
                "url": point.payload["section_url"],
                "breadcrumbs": " > ".join(point.payload["breadcrumbs"]),
                "score": point.score,
                "snippet": point.payload["chunk_text"][:100] + "...",
            }
        )
    return formatted


print("\n6️⃣ 포맷팅된 검색 결과:")

query = "HNSW 설정"
results = hybrid_search(query, limit=3)
formatted = format_search_results(query, results)

for item in formatted:
    print(f"\n{item['rank']}. {item['title']}")
    print(f"   페이지: {item['page']}")
    print(f"   경로: {item['breadcrumbs']}")
    print(f"   URL: {item['url']}")
    print(f"   점수: {item['score']:.4f}")
    print(f"   요약: {item['snippet']}")

# 8. 프로덕션 고려사항
print("\n" + "=" * 60)
print("프로덕션 고려사항")
print("=" * 60)

print(
    """
1. 청킹 전략
   - 섹션 단위 청킹: 사용자가 기대하는 구조 유지
   - 이전/다음 섹션 컨텍스트 포함
   - 메타데이터로 탐색 및 필터링 지원

2. 페이로드 설계
   - 표시에 필요한 필드: 제목, URL, breadcrumbs
   - 필터링에 필요한 필드: 태그, 카테고리
   - 평가에 필요한 필드: 섹션 URL, 태그

3. 검색 파이프라인
   - 하이브리드 검색: Dense + Sparse
   - 재랭킹: ColBERT로 정밀도 향상
   - 후보 수 조정: 속도와 정확도 균형

4. 성능 최적화
   - Payload Index: 자주 필터링하는 필드
   - HNSW 설정: 검색 속도 조정
   - 후보 수: 너무 많으면 느림, 너무 적으면 누락

5. 평가 지표
   - Recall@K: 관련 결과를 찾는 능력
   - MRR: 최상위 결과의 품질
   - 지연시간: 사용자 경험
"""
)

# 9. 성공 기준 체크리스트
print("\n" + "=" * 60)
print("성공 기준 체크리스트")
print("=" * 60)

checklist = [
    ("✅", "엔드투엔드 실행 가능한 코드"),
    ("✅", "하이브리드 검색 구현 (Dense + Sparse + ColBERT)"),
    ("✅", "평가 프레임워크 (Recall@10, MRR, 지연시간)"),
    ("✅", "성능 지표 측정"),
    ("✅", "결과 포맷팅 및 표시"),
    ("✅", "프로덕션 고려사항 문서화"),
]

for status, item in checklist:
    print(f"{status} {item}")

print("\n✅ 최종 프로젝트 튜토리얼 완료!")
print("\n다음 단계:")
print("  - 실제 문서 데이터로 확장")
print("  - 더 많은 평가 쿼리 추가")
print("  - 성능 튜닝 실험")
print("  - 프로덕션 배포 준비")
