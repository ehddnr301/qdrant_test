# data_hr.py
GLOSSARY = [
    {
        "id": 1,  # g-emp
        "original_id": "g-emp",
        "title": "사번",
        "description": "사원 고유키",
        "synonyms": ["사번", "직원ID", "employee id", "uid"],
    },
    {
        "id": 2,  # g-hq
        "original_id": "g-hq",
        "title": "본사",
        "description": "직원의 근무지가 서울 본사인 경우",
        "synonyms": ["본사", "서울본사", "HQ"],
    },
    {
        "id": 3,  # g-new
        "original_id": "g-new",
        "title": "신입",
        "description": "입사 1년 미만",
        "synonyms": ["신입", "입사 1년 미만", "new hire"],
    },
    {
        "id": 4,  # g-active
        "original_id": "g-active",
        "title": "재직자",
        "description": "현재 재직 중인 직원",
        "synonyms": ["재직자", "현직자", "active employee", "현재 직원"],
    },
    {
        "id": 5,  # g-dept
        "original_id": "g-dept",
        "title": "부서",
        "description": "직원이 소속된 조직 단위",
        "synonyms": ["부서", "팀", "department", "team"],
    },
    {
        "id": 6,  # g-title
        "original_id": "g-title",
        "title": "직급",
        "description": "직원의 직위나 계급",
        "synonyms": ["직급", "직위", "title", "position", "rank"],
    },
    {
        "id": 7,  # g-attendance
        "original_id": "g-attendance",
        "title": "근태",
        "description": "출근, 결근, 지각 등의 근무 상태",
        "synonyms": ["근태", "출석", "attendance", "근무상태"],
    },
    {
        "id": 8,  # g-salary
        "original_id": "g-salary",
        "title": "연봉",
        "description": "직원의 연간 급여 금액",
        "synonyms": ["연봉", "급여", "salary", "연봉금액"],
    },
]

SQL_HISTORY = [
    {
        "id": 101,  # h-001
        "original_id": "h-001",
        "title": "부서별 인원",
        "description": "현재 재직자만 집계",
        "sql": """SELECT d.dept_name, count() AS headcount
FROM employees e JOIN departments d ON e.dept_id=d.dept_id
WHERE e.employment_status='ACTIVE'
GROUP BY d.dept_name
ORDER BY headcount DESC;""",
    },
    {
        "id": 102,  # h-002
        "original_id": "h-002",
        "title": "결근 3회 이상(지난달)",
        "description": "attendance 기반",
        "sql": """WITH last_month AS (SELECT toStartOfMonth(addMonths(today(), -1)) AS m)
SELECT e.emp_id, e.name, countIf(a.status='ABSENT') AS absences
FROM attendance a JOIN employees e ON e.emp_id=a.emp_id
CROSS JOIN last_month
WHERE a.att_date >= m AND a.att_date < addMonths(m,1)
GROUP BY e.emp_id, e.name HAVING absences>=3
ORDER BY absences DESC;""",
    },
    {
        "id": 103,  # h-003
        "original_id": "h-003",
        "title": "본사 직원 목록",
        "description": "서울 본사에 근무하는 재직자 목록",
        "sql": """SELECT e.emp_id, e.name, e.title, d.dept_name, e.hire_date
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
WHERE e.location = 'Seoul-HQ' AND e.employment_status = 'ACTIVE'
ORDER BY e.name;""",
    },
    {
        "id": 104,  # h-004
        "original_id": "h-004",
        "title": "직급별 평균 연봉",
        "description": "직급별로 그룹화하여 평균 연봉 계산",
        "sql": """SELECT title, 
       count() AS headcount,
       avg(salary) AS avg_salary,
       min(salary) AS min_salary,
       max(salary) AS max_salary
FROM employees
WHERE employment_status = 'ACTIVE'
GROUP BY title
ORDER BY avg_salary DESC;""",
    },
    {
        "id": 105,  # h-005
        "original_id": "h-005",
        "title": "입사 연도별 인원",
        "description": "입사 연도별로 직원 수 집계",
        "sql": """SELECT toYear(hire_date) AS hire_year,
       count() AS headcount
FROM employees
WHERE employment_status = 'ACTIVE'
GROUP BY hire_year
ORDER BY hire_year DESC;""",
    },
    {
        "id": 106,  # h-006
        "original_id": "h-006",
        "title": "지각 횟수 조회(이번 달)",
        "description": "이번 달 지각한 직원과 지각 횟수",
        "sql": """WITH this_month AS (SELECT toStartOfMonth(today()) AS m)
SELECT e.emp_id, e.name, d.dept_name, countIf(a.status='LATE') AS late_count
FROM attendance a
JOIN employees e ON e.emp_id = a.emp_id
JOIN departments d ON e.dept_id = d.dept_id
CROSS JOIN this_month
WHERE a.att_date >= m AND a.att_date < addMonths(m, 1)
  AND e.employment_status = 'ACTIVE'
GROUP BY e.emp_id, e.name, d.dept_name
HAVING late_count > 0
ORDER BY late_count DESC;""",
    },
    {
        "id": 107,  # h-007
        "original_id": "h-007",
        "title": "부서별 평균 연봉",
        "description": "부서별 평균 연봉과 인원수 집계",
        "sql": """SELECT d.dept_name,
       count() AS headcount,
       avg(e.salary) AS avg_salary,
       sum(e.salary) AS total_salary
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
WHERE e.employment_status = 'ACTIVE'
GROUP BY d.dept_name
ORDER BY avg_salary DESC;""",
    },
]

CATALOG = {
    "tables": [
        {
            "table": "employees",
            "description": "직원 마스터",
            "columns": [
                {"name": "emp_id", "dtype": "UInt64", "description": "사번"},
                {"name": "name", "dtype": "String", "description": "이름"},
                {"name": "title", "dtype": "String", "description": "직급"},
                {"name": "dept_id", "dtype": "UInt32", "description": "부서키"},
                {
                    "name": "location",
                    "dtype": "String",
                    "description": "근무지(Seoul-HQ 등)",
                },
                {"name": "hire_date", "dtype": "Date", "description": "입사일"},
                {
                    "name": "employment_status",
                    "dtype": "Enum('ACTIVE','LEFT')",
                    "description": "재직/퇴사",
                },
                {"name": "salary", "dtype": "UInt32", "description": "연봉(만원)"},
            ],
        },
        {
            "table": "departments",
            "description": "부서 테이블",
            "columns": [
                {"name": "dept_id", "dtype": "UInt32", "description": "부서키"},
                {"name": "dept_name", "dtype": "String", "description": "부서명"},
            ],
        },
        {
            "table": "attendance",
            "description": "근태 기록",
            "columns": [
                {"name": "att_date", "dtype": "Date", "description": "근태일자"},
                {"name": "emp_id", "dtype": "UInt64", "description": "사번"},
                {
                    "name": "status",
                    "dtype": "Enum('PRESENT','ABSENT','LATE')",
                    "description": "근태상태",
                },
            ],
        },
        {
            "table": "leave_records",
            "description": "휴가 기록",
            "columns": [
                {"name": "leave_id", "dtype": "UInt64", "description": "휴가ID"},
                {"name": "emp_id", "dtype": "UInt64", "description": "사번"},
                {"name": "leave_start", "dtype": "Date", "description": "휴가 시작일"},
                {"name": "leave_end", "dtype": "Date", "description": "휴가 종료일"},
                {
                    "name": "leave_type",
                    "dtype": "Enum('ANNUAL','SICK','MISC')",
                    "description": "휴가 유형(연차/병가/기타)",
                },
                {"name": "days", "dtype": "UInt8", "description": "휴가 일수"},
                {
                    "name": "status",
                    "dtype": "Enum('PENDING','APPROVED','REJECTED')",
                    "description": "승인 상태",
                },
            ],
        },
        {
            "table": "performance_reviews",
            "description": "성과평가",
            "columns": [
                {"name": "review_id", "dtype": "UInt64", "description": "평가ID"},
                {"name": "emp_id", "dtype": "UInt64", "description": "사번"},
                {"name": "review_date", "dtype": "Date", "description": "평가일자"},
                {
                    "name": "reviewer_id",
                    "dtype": "UInt64",
                    "description": "평가자 사번",
                },
                {"name": "score", "dtype": "UInt8", "description": "평가 점수(1-100)"},
                {"name": "comments", "dtype": "String", "description": "평가 의견"},
            ],
        },
        {
            "table": "salary_history",
            "description": "급여 이력",
            "columns": [
                {"name": "salary_id", "dtype": "UInt64", "description": "급여ID"},
                {"name": "emp_id", "dtype": "UInt64", "description": "사번"},
                {"name": "effective_date", "dtype": "Date", "description": "적용일자"},
                {"name": "salary", "dtype": "UInt32", "description": "연봉(만원)"},
                {
                    "name": "change_reason",
                    "dtype": "String",
                    "description": "변경 사유",
                },
            ],
        },
        {
            "table": "projects",
            "description": "프로젝트",
            "columns": [
                {"name": "project_id", "dtype": "UInt64", "description": "프로젝트ID"},
                {
                    "name": "project_name",
                    "dtype": "String",
                    "description": "프로젝트명",
                },
                {"name": "start_date", "dtype": "Date", "description": "시작일"},
                {"name": "end_date", "dtype": "Date", "description": "종료일"},
                {
                    "name": "status",
                    "dtype": "Enum('PLANNING','ONGOING','COMPLETED','CANCELLED')",
                    "description": "프로젝트 상태",
                },
                {"name": "dept_id", "dtype": "UInt32", "description": "담당 부서키"},
            ],
        },
        {
            "table": "project_assignments",
            "description": "프로젝트 배정",
            "columns": [
                {"name": "assignment_id", "dtype": "UInt64", "description": "배정ID"},
                {"name": "project_id", "dtype": "UInt64", "description": "프로젝트ID"},
                {"name": "emp_id", "dtype": "UInt64", "description": "사번"},
                {"name": "role", "dtype": "String", "description": "역할"},
                {"name": "assign_date", "dtype": "Date", "description": "배정일자"},
                {
                    "name": "hours_per_week",
                    "dtype": "UInt8",
                    "description": "주당 투입시간",
                },
            ],
        },
    ]
}
