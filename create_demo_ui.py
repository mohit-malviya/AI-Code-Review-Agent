"""
Helper script to generate a fresh demo approval request with rich code diffs
so you can test and preview the Approval UI in your browser immediately.
"""
from app.services.approval_service import create_approval_request

demo_fixes = [
    {
        "file": "app/services/auth_service.py",
        "summary": "Fix critical SQL injection vulnerability and hardcoded secret",
        "category": "security",
        "severity": "critical",
        "line": 42,
        "original_code": (
            'def get_user_by_token(token):\n'
            '    SECRET = "dummy_mock_auth_secret_xyz"\n'
            '    query = f"SELECT * FROM users WHERE auth_token = \'{token}\'"\n'
            '    return db.execute(query)\n'
        ),
        "fixed_code": (
            'def get_user_by_token(token: str) -> dict | None:\n'
            '    secret = os.getenv("AUTH_SECRET_KEY")\n'
            '    query = "SELECT * FROM users WHERE auth_token = :token"\n'
            '    return db.execute(query, {"token": token})\n'
        ),
        "changes": [
            "Replaced string interpolation with parameterized SQL query to prevent SQL injection.",
            "Replaced hardcoded SECRET string with environment variable lookup.",
            "Added Python type hints.",
        ],
    },
    {
        "file": "app/utils/math_helpers.py",
        "summary": "Fix ZeroDivisionError when calculating average of empty list",
        "category": "bug",
        "severity": "high",
        "line": 15,
        "original_code": (
            'def calculate_average(items):\n'
            '    return sum(items) / len(items)\n'
        ),
        "fixed_code": (
            'def calculate_average(items: list[float]) -> float:\n'
            '    if not items:\n'
            '        return 0.0\n'
            '    return sum(items) / len(items)\n'
        ),
        "changes": [
            "Added zero-length guard check to prevent ZeroDivisionError crash.",
            "Added return type annotations.",
        ],
    },
]

req = create_approval_request(
    owner="mohitmalviya-skilltect",
    repository="AI-Code-Review-Agent",
    pull_request_number=42,
    commit_sha="a7b8c9d0e1f2",
    proposed_fixes=demo_fixes,
)

approval_id = req["approval_id"]
local_url = f"http://localhost:8000/approval/{approval_id}"
ngrok_url = f"https://antiques-wildcard-stubble.ngrok-free.dev/approval/{approval_id}"

print("\n" + "=" * 65)
print("DEMO APPROVAL UI GENERATED SUCCESSFULLY!")
print("=" * 65)
print(f"Approval ID:  {approval_id}")
print(f"\n>> Open in Browser (Local):")
print(f"   {local_url}")
print(f"\n>> Open in Browser (Public Ngrok):")
print(f"   {ngrok_url}")
print("=" * 65 + "\n")
