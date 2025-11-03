# check_updates.py
"""
Qdrant 벡터 데이터베이스 변경 내역 조회
- update_demo.py에서 수행한 업데이트 내역을 확인
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import OpenAI
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

qc = QdrantClient(url="http://localhost:6333")

print("=" * 80)
print("변경 내역 조회 데모")
print("=" * 80)
print()

# =============================================================================
# (1) 특정 포인트의 변경 이력 조회
# =============================================================================
print("[1] 특정 포인트(ID: 1, 사번)의 변경 이력")
print()

point = qc.retrieve(
    collection_name="hr_glossary",
    ids=[1],
    with_payload=True,
    with_vectors=False,
)

if point and point[0].payload:
    payload = point[0].payload
    title = payload.get("title", "N/A")
    description = payload.get("description", "N/A")
    synonyms = payload.get("synonyms", [])
    update_history = payload.get("update_history", [])

    print(f"  제목: {title}")
    print(f"  설명: {description}")
    print(f"  동의어: {', '.join(synonyms)}")
    print()

    if update_history:
        print(f"  변경 이력 ({len(update_history)}건):")
        for idx, history in enumerate(update_history, 1):
            timestamp = history.get("timestamp", "N/A")
            field = history.get("field", "N/A")
            reason = history.get("reason", "N/A")

            # 타임스탬프 포맷팅
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = timestamp

            print(f"    [{idx}] {formatted_time}")
            print(f"        필드: {field}")
            print(f"        사유: {reason}")
            if history.get("old_value") and history.get("new_value"):
                old_val = history.get("old_value")
                new_val = history.get("new_value")
                if isinstance(old_val, list):
                    print(
                        f"        이전 ({len(old_val)}개): {', '.join(str(v) for v in old_val[:5])}{'...' if len(old_val) > 5 else ''}"
                    )
                    print(
                        f"        이후 ({len(new_val)}개): {', '.join(str(v) for v in new_val[:5])}{'...' if len(new_val) > 5 else ''}"
                    )
                    # 변경사항 강조
                    added = set(new_val) - set(old_val)
                    removed = set(old_val) - set(new_val)
                    if added:
                        print(
                            f"        ✨ 추가됨: {', '.join(str(v) for v in list(added)[:3])}{'...' if len(added) > 3 else ''}"
                        )
                    if removed:
                        print(
                            f"        🗑️  제거됨: {', '.join(str(v) for v in list(removed)[:3])}{'...' if len(removed) > 3 else ''}"
                        )
                else:
                    print(
                        f"        🔴 이전: {old_val[:80] if len(str(old_val)) > 80 else old_val}"
                    )
                    print(
                        f"        🟢 이후: {new_val[:80] if len(str(new_val)) > 80 else new_val}"
                    )
                    # 완전히 다른 내용인 경우 강조
                    if str(old_val) != str(new_val):
                        print(f"        ⚠️  완전히 다른 내용으로 변경되었습니다!")
            print()
    else:
        print("  변경 이력이 없습니다.")

print()

# =============================================================================
# (2) 최근 업데이트된 항목들 조회 (update_history 필드가 있는 모든 항목)
# =============================================================================
print("[2] 최근 업데이트된 모든 항목 조회")
print()

# hr_glossary 컬렉션의 모든 포인트 스크롤
all_points, _ = qc.scroll(
    collection_name="hr_glossary",
    limit=100,
    with_payload=True,
    with_vectors=False,
)

updated_points = []
for point in all_points:
    if point.payload and point.payload.get("update_history"):
        update_history = point.payload.get("update_history", [])
        if update_history:
            # 가장 최근 업데이트 시간 찾기
            latest_timestamp = max(
                [h.get("timestamp", "") for h in update_history if h.get("timestamp")],
                default="",
            )
            updated_points.append(
                {
                    "id": point.id,
                    "title": point.payload.get("title", "N/A"),
                    "latest_update": latest_timestamp,
                    "update_count": len(update_history),
                }
            )

# 최근 업데이트 순으로 정렬
updated_points.sort(key=lambda x: x["latest_update"], reverse=True)

if updated_points:
    print(f"  총 {len(updated_points)}개 항목이 최근에 업데이트되었습니다:")
    print()
    for idx, point_info in enumerate(updated_points[:10], 1):  # 최대 10개만 표시
        print(f"  [{idx}] ID {point_info['id']}: {point_info['title']}")
        print(f"      업데이트 횟수: {point_info['update_count']}회")

        if point_info["latest_update"]:
            try:
                dt = datetime.fromisoformat(point_info["latest_update"])
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                print(f"      최근 업데이트: {formatted_time}")
            except:
                print(f"      최근 업데이트: {point_info['latest_update']}")
        print()
else:
    print("  최근 업데이트된 항목이 없습니다.")

print()

# =============================================================================
# (3) 특정 필드가 변경된 항목 검색 (예: synonyms 필드)
# =============================================================================
print("[3] 특정 필드(synonyms)가 업데이트된 항목 검색")
print()

synonyms_updated = []
for point in all_points:
    if point.payload:
        update_history = point.payload.get("update_history", [])
        # synonyms 필드가 변경된 이력이 있는지 확인
        for history in update_history:
            if history.get("field") == "synonyms":
                synonyms_updated.append(
                    {
                        "id": point.id,
                        "title": point.payload.get("title", "N/A"),
                        "synonyms": point.payload.get("synonyms", []),
                    }
                )
                break

if synonyms_updated:
    print(f"  synonyms 필드가 업데이트된 항목: {len(synonyms_updated)}개")
    print()
    for idx, item in enumerate(synonyms_updated, 1):
        print(f"  [{idx}] ID {item['id']}: {item['title']}")
        print(f"      현재 동의어 수: {len(item['synonyms'])}개")
        print(
            f"      동의어: {', '.join(item['synonyms'][:5])}{'...' if len(item['synonyms']) > 5 else ''}"
        )
        print()
else:
    print("  synonyms 필드가 업데이트된 항목이 없습니다.")

print()

# =============================================================================
# (4) 변경 통계
# =============================================================================
print("[4] 변경 통계")
print()

total_updates = 0
field_counts = {}
reason_counts = {}

for point in all_points:
    if point.payload and point.payload.get("update_history"):
        for history in point.payload.get("update_history", []):
            total_updates += 1
            field = history.get("field", "unknown")
            reason = history.get("reason", "unknown")

            field_counts[field] = field_counts.get(field, 0) + 1
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

print(f"  총 변경 건수: {total_updates}건")
print(f"  변경된 항목 수: {len(updated_points)}개")
print()
print("  필드별 변경 건수:")
for field, count in sorted(field_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"    - {field}: {count}건")
print()
print("  변경 사유별 통계:")
for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"    - {reason}: {count}건")

print()

# =============================================================================
# (5) 업데이트 전후 비교 (예시)
# =============================================================================
print("[5] 업데이트 전후 비교 (ID: 1)")
print()

# ID 1 포인트 다시 조회
point = qc.retrieve(
    collection_name="hr_glossary",
    ids=[1],
    with_payload=True,
    with_vectors=False,
)

if point and point[0].payload:
    payload = point[0].payload
    update_history = payload.get("update_history", [])

    if update_history:
        # synonyms 필드의 변경 이력 찾기
        synonyms_history = [h for h in update_history if h.get("field") == "synonyms"]

        if synonyms_history:
            latest = synonyms_history[-1]
            old_synonyms = latest.get("old_value", [])
            new_synonyms = latest.get("new_value", [])

            print("  synonyms 필드 변경 내역:")
            print()
            print(f"    🔴 이전 동의어 ({len(old_synonyms)}개):")
            for idx, syn in enumerate(old_synonyms, 1):
                print(f"      [{idx}] {syn}")
            print()
            print(f"    🟢 이후 동의어 ({len(new_synonyms)}개):")
            for idx, syn in enumerate(new_synonyms, 1):
                print(f"      [{idx}] {syn}")
            print()

            # 새로 추가된 동의어 찾기
            added = set(new_synonyms) - set(old_synonyms)
            removed = set(old_synonyms) - set(new_synonyms)

            if added:
                print(f"    ✨ 새로 추가된 동의어 ({len(added)}개):")
                for idx, syn in enumerate(added, 1):
                    print(f"      [{idx}] {syn}")
            if removed:
                print()
                print(f"    🗑️  제거된 동의어 ({len(removed)}개):")
                for idx, syn in enumerate(removed, 1):
                    print(f"      [{idx}] {syn}")
        else:
            print("  synonyms 필드 변경 이력이 없습니다.")
    else:
        print("  변경 이력이 없습니다.")

print()
print("=" * 80)
print("변경 내역 조회 완료")
print("=" * 80)
