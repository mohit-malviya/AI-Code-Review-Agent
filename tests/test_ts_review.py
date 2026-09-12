"""
Test script to run the AI Code Review Agent pipeline on a TypeScript file.
"""
from app.services.git_service import SUPPORTED_EXTENSIONS
from app.services.llm_service import review_code
from app.services.code_fix_service import generate_code_fix


def test_typescript_pipeline():
    # 1. Verify .ts is recognized as a supported extension
    assert ".ts" in SUPPORTED_EXTENSIONS, ".ts must be in SUPPORTED_EXTENSIONS"

    # 2. Read the TypeScript demo file
    with open("tests/demo_service.ts", "r", encoding="utf-8") as f:
        ts_code = f.read()

    # 3. Request Gemini to review the TypeScript file
    review_context = f"FILE: tests/demo_service.ts\n```typescript\n{ts_code}\n```"
    review_result = review_code(review_context)

    issues = review_result.get("issues", [])
    assert len(issues) > 0, "Agent should detect TypeScript issues in demo_service.ts"

    print("=" * 65)
    print("TYPESCRIPT AI CODE REVIEW RESULTS")
    print("=" * 65)
    print("Summary:", review_result.get("summary"))
    print(f"Total issues detected: {len(issues)}\n")

    for i, issue in enumerate(issues, 1):
        print(f"Issue {i}: [{issue.get('category').upper()}] ({issue.get('severity').upper()}) at line {issue.get('line')}")
        print(f"  Problem:    {issue.get('problem')}")
        print(f"  Suggestion: {issue.get('suggestion')}\n")

    # 4. Generate AI code fix for the first issue
    first_issue = issues[0]
    fix = generate_code_fix("tests/demo_service.ts", ts_code, first_issue)

    print("=" * 65)
    print("AI PROPOSED FIX FOR FIRST TYPESCRIPT ISSUE")
    print("=" * 65)
    print("Summary:", fix.get("summary"))
    print("Changes:", fix.get("changes"))
    print("\nFixed Code:\n")
    print(fix.get("fixed_code"))
    print("=" * 65)


if __name__ == "__main__":
    test_typescript_pipeline()
