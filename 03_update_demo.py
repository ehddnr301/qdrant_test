# update_demo.py
"""
Qdrant 벡터 데이터베이스 업데이트 예제
- 배치 업데이트, 변경 이력 추적, 조건부 업데이트 등 실제 운영 환경 패턴
"""
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType, Filter, FieldCondition, MatchValue
from openai import OpenAI
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

qc = QdrantClient(url="http://localhost:6333")

# OpenAI 클라이언트 초기화
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """OpenAI API를 사용하여 텍스트를 벡터로 변환"""
    response = openai_client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


print("=" * 80)
print("벡터 데이터베이스 업데이트 데모")
print("=" * 80)
print()

# =============================================================================
# (1) 배치 업데이트: 여러 용어의 동의어를 한 번에 업데이트
# =============================================================================
print("[1] 배치 업데이트: 여러 용어의 동의어 추가")
print()

# 업데이트할 용어들 (ID와 새로운 동의어 목록) - 말도 안 되는 예시로 변경
updates = [
    {
        "id": 1,  # 사번
        "new_synonyms": [
            "사번",
            "직원ID",
            "우주의 고유번호",
            "외계인 식별자",
            "마법의 숫자",
            "시간 여행 티켓",
            "코스모스 ID",
        ],
        "reason": "상상력이 풍부한 동의어 추가 (데모용)",
    },
    {
        "id": 5,  # 부서
        "new_synonyms": [
            "부서",
            "팀",
            "드래곤의 둥지",
            "우주선 함대",
            "마법사 길드",
            "시간의 방",
        ],
        "reason": "판타지 요소 추가 (데모용)",
    },
    {
        "id": 6,  # 직급
        "new_synonyms": [
            "직급",
            "직위",
            "용사 계급",
            "마법사 레벨",
            "우주 대장",
            "시간 주인",
        ],
        "reason": "게임 세계관 반영 (데모용)",
    },
]

update_history = []  # 변경 이력 기록

for update in updates:
    # 기존 payload 조회
    existing = qc.retrieve(
        collection_name="hr_glossary",
        ids=[update["id"]],
        with_payload=True,
        with_vectors=False,
    )

    if existing:
        old_payload = existing[0].payload
        old_synonyms = old_payload.get("synonyms", []) if old_payload else []

        # 업데이트 실행
        qc.set_payload(
            collection_name="hr_glossary",
            payload={"synonyms": update["new_synonyms"]},
            points=[update["id"]],
        )

        # 변경 이력 기록
        update_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "collection_name": "hr_glossary",
                "point_id": update["id"],
                "field": "synonyms",
                "old_value": old_synonyms,
                "new_value": update["new_synonyms"],
                "reason": update["reason"],
            }
        )

        print(f"  ✓ ID {update['id']}: {update['reason']}")
        print(
            f"    이전: {len(old_synonyms)}개 → 이후: {len(update['new_synonyms'])}개"
        )

print()

# =============================================================================
# (2) 조건부 업데이트: 특정 조건을 만족하는 항목만 업데이트
# =============================================================================
print("[2] 조건부 업데이트: 특정 테이블의 컬럼 설명 개선")
print()

# employees 테이블의 컬럼들 중 salary 컬럼 설명 개선
updated_columns = qc.scroll(
    collection_name="hr_catalog",
    scroll_filter=Filter(
        must=[
            FieldCondition(key="level", match=MatchValue(value="column")),
            FieldCondition(key="table", match=MatchValue(value="employees")),
            FieldCondition(key="column", match=MatchValue(value="salary")),
        ]
    ),
    limit=10,
    with_payload=True,
    with_vectors=False,
)

if updated_columns[0]:  # points가 있는 경우
    point = updated_columns[0][0]
    old_description = point.payload.get("description", "") if point.payload else ""
    new_description = "우주 보석의 가치 (별의 결정체로 계산, 1만원 = 행성 1개)"

    if old_description != new_description:
        qc.set_payload(
            collection_name="hr_catalog",
            payload={"description": new_description},
            points=[point.id],
        )

        update_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "collection_name": "hr_catalog",
                "point_id": point.id,
                "field": "description",
                "old_value": old_description,
                "new_value": new_description,
                "reason": "우주 판타지 세계관으로 설명 변경 (데모용)",
            }
        )

        print(f"  ✓ ID {point.id} (employees.salary): 설명 개선")
        print(f"    이전: {old_description}")
        print(f"    이후: {new_description}")

print()

# =============================================================================
# (3) 벡터 재임베딩: 설명이 변경되어 의미 표현이 개선된 경우
# =============================================================================
print("[3] 벡터 재임베딩: 개선된 설명으로 벡터 업데이트")
print()

# 사번 용어의 설명을 더 상세하게 만들고 재임베딩
emp_point = qc.retrieve(
    collection_name="hr_glossary",
    ids=[1],
    with_payload=True,
    with_vectors=False,
)

if emp_point:
    old_desc = (
        emp_point[0].payload.get("description", "") if emp_point[0].payload else ""
    )
    new_desc = "우주를 관장하는 마법사의 고유 번호 (시간의 흐름을 제어하는 키, 차원을 넘나드는 식별자)"

    # 재임베딩을 위한 텍스트 생성
    synonyms_text = ", ".join(
        updates[0]["new_synonyms"]
    )  # 위에서 업데이트한 동의어 사용
    embedding_text = f"사번 :: {new_desc} :: {synonyms_text}"
    new_vector = get_embedding(embedding_text)

    # 벡터 업데이트
    qc.update_vectors(
        collection_name="hr_glossary",
        points=[{"id": 1, "vector": new_vector}],
    )

    # 설명도 함께 업데이트
    qc.set_payload(
        collection_name="hr_glossary",
        payload={"description": new_desc},
        points=[1],
    )

    update_history.append(
        {
            "timestamp": datetime.now().isoformat(),
            "collection_name": "hr_glossary",
            "point_id": 1,
            "field": "vector + description",
            "old_value": old_desc,
            "new_value": new_desc,
            "reason": "판타지 세계관 설명으로 벡터 재임베딩 및 설명 완전 변경 (데모용)",
        }
    )

    print(f"  ✓ ID 1 (사번): 벡터 및 설명 재임베딩 완료")

print()

# =============================================================================
# (4) 변경 이력을 payload에 기록
# =============================================================================
print("[4] 변경 이력을 메타데이터로 저장")
print()

# 각 컬렉션에 변경 이력 필드 추가 (실제 운영에서는 별도 이력 테이블/컬렉션 권장)
if update_history:
    # 모든 변경 이력 저장 (변경사항을 잘 보이게 하기 위해)
    all_history = update_history

    for history_item in all_history:
        point_id = history_item["point_id"]
        collection_name = history_item.get("collection_name", "hr_glossary")

        # update_history 필드가 이미 있으면 추가, 없으면 생성
        existing = qc.retrieve(
            collection_name=collection_name,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )

        if existing and existing[0].payload:
            existing_history = existing[0].payload.get("update_history", [])
            existing_history.append(history_item)
            # 최근 5개만 유지
            existing_history = existing_history[-5:]
            qc.set_payload(
                collection_name=collection_name,
                payload={"update_history": existing_history},
                points=[point_id],
            )
        else:
            qc.set_payload(
                collection_name=collection_name,
                payload={"update_history": [history_item]},
                points=[point_id],
            )

    print(f"  ✓ {len(all_history)}개 항목의 변경 이력 저장 완료")

print()

# =============================================================================
# (5) 인덱스 최적화
# =============================================================================
print("[5] 조회 성능 최적화를 위한 인덱스 추가")
print()

try:
    qc.create_payload_index("hr_sql_history", "title", PayloadSchemaType.TEXT)
    print("  ✓ hr_sql_history.title 인덱스 생성 완료")
except Exception as e:
    print(f"  ⚠️  인덱스 생성 건너뜀: {e}")

try:
    qc.create_payload_index("hr_glossary", "title", PayloadSchemaType.KEYWORD)
    print("  ✓ hr_glossary.title 인덱스 생성 완료")
except Exception as e:
    print(f"  ⚠️  인덱스 생성 건너뜀: {e}")

print()

# =============================================================================
# 요약
# =============================================================================
print("=" * 80)
print("업데이트 요약")
print("=" * 80)
print(f"총 업데이트 항목 수: {len(update_history)}개")
print()
print("변경 내역:")
for idx, history in enumerate(update_history, 1):
    print(f"  [{idx}] ID {history['point_id']}: {history['field']}")
    print(f"      사유: {history['reason']}")
    print(f"      시각: {history['timestamp']}")

print()
print("✅ 모든 업데이트 작업 완료")
print("💡 변경 내역 조회는 'check_updates.py' 파일을 실행하세요")
print()
