# qdrant_setup.py
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
    HnswConfigDiff,
    OptimizersConfigDiff,
)
from openai import OpenAI
import os
from dummy_data_hr import GLOSSARY, SQL_HISTORY, CATALOG

from dotenv import load_dotenv

load_dotenv()

client = QdrantClient(url="http://localhost:6333")

# OpenAI 클라이언트 초기화 (API 키는 환경변수 OPENAI_API_KEY에서 가져옴)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 임베딩 함수
def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """OpenAI API를 사용하여 텍스트를 벡터로 변환"""
    response = openai_client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


# text-embedding-3-small 모델의 기본 벡터 차원 (1536)
# 다른 모델 사용 시 차원 수를 변경해야 함:
# - text-embedding-3-small: 1536 (기본) 또는 512로 축소 가능
# - text-embedding-3-large: 3072 (기본) 또는 256으로 축소 가능
# - text-embedding-ada-002: 1536
VSIZE = 1536  # OpenAI text-embedding-3-small 모델의 벡터 차원


def ensure_collection(name: str):
    # 컬렉션 생성(존재 시 스킵)
    names = [c.name for c in client.get_collections().collections]
    if name in names:
        return
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=VSIZE, distance=Distance.COSINE, on_disk=True),
        hnsw_config=HnswConfigDiff(m=16, ef_construct=200),
        optimizers_config=OptimizersConfigDiff(
            memmap_threshold=20000
        ),  # 큰 payload에 유리
    )


# 1) Glossary
ensure_collection("hr_glossary")
client.create_payload_index("hr_glossary", "type", PayloadSchemaType.KEYWORD)
g_points = []
for g in GLOSSARY:
    text = f"{g['title']} :: {g['description']} :: {', '.join(g['synonyms'])}"
    g_points.append(
        PointStruct(
            id=g["id"],
            vector=get_embedding(text),
            payload={
                "type": "glossary",
                "original_id": g["original_id"],
                "title": g["title"],
                "description": g["description"],
                "synonyms": g["synonyms"],
            },
        )
    )
client.upsert("hr_glossary", g_points)

# 2) SQL History
ensure_collection("hr_sql_history")
client.create_payload_index("hr_sql_history", "type", PayloadSchemaType.KEYWORD)
h_points = []
for h in SQL_HISTORY:
    text = f"{h['title']} :: {h['description']} :: {h['sql']}"
    h_points.append(
        PointStruct(
            id=h["id"],
            vector=get_embedding(text),
            payload={
                "type": "history",
                "original_id": h["original_id"],
                "title": h["title"],
                "description": h["description"],
                "sql": h["sql"],
            },
        )
    )
client.upsert("hr_sql_history", h_points)

# 3) Data Catalog (테이블 단위로 저장 - temp.py와 같은 방식)
ensure_collection("hr_catalog")
cat_points = []
point_id_counter = 1000
for t in CATALOG["tables"]:
    # temp.py처럼 테이블 전체 정보를 하나로 저장
    cols = "\n".join(
        [
            f"{col['name']}: {col.get('description','')} :: {col['dtype']}"
            for col in t["columns"]
        ]
    )
    text_content = f"{t['table']}: {t['description']}\nColumns:\n {cols}"

    cat_points.append(
        PointStruct(
            id=point_id_counter,
            vector=get_embedding(text_content),
            payload={
                "table": t["table"],
                "description": t["description"],
                "columns": t["columns"],  # 전체 컬럼 정보를 배열로 저장
            },
        )
    )
    point_id_counter += 1
client.upsert("hr_catalog", cat_points)

print("✅ Upsert 완료")
