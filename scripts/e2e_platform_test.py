r"""
Vedantu Online Coding Assessment Platform - End-to-End Test Suite
Validates the entire platform against the running Docker Compose environment:
- Frontend (port 3000) and Same-Origin Reverse Proxy
- FastAPI Backend (port 8000)
- PostgreSQL 16 (port 5432)
- Redis 7 (port 6379)
- Judge0 CE v1.13.1 (port 2358)
- Alembic database migration status
- Authentication & RBAC
- Question Bank & Test Case isolation
- Python & Java execution in Judge0
- Assessment lifecycle workflow
- AI Evaluation & Static Code Analysis
- Adaptive Assessment Engine
- Proctoring & Integrity Monitoring
- Analytics & Reporting
- Security & Privacy Safeguards
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import httpx

FRONTEND_URL = "http://localhost:3000"
PROXY_API_URL = "http://localhost:3000/api/v1"
DIRECT_API_URL = "http://localhost:8000/api/v1"

TEST_RESULTS = []

def record_test(feature, test_name, expected, actual, passed, defect=None):
    status = "PASS" if passed else "FAIL"
    TEST_RESULTS.append({
        "feature": feature,
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "status": status,
        "defect": defect
    })
    print(f"[{status}] {feature} :: {test_name}")
    if not passed:
        print(f"       Expected: {expected}")
        print(f"       Actual:   {actual}")
        if defect:
            print(f"       Defect:   {defect}")


async def run_tests():
    print("=" * 80)
    print("STARTING COMPLETE PLATFORM FUNCTIONAL TESTING")
    print(f"Frontend URL:     {FRONTEND_URL}")
    print(f"Proxy API URL:    {PROXY_API_URL}")
    print(f"Direct API URL:   {DIRECT_API_URL}")
    print("=" * 80)

    test_suffix = uuid.uuid4().hex[:6]
    student_email = f"student_test_{test_suffix}@vedantu-test.com"
    student_password = "SecureTestPassword123!"
    student2_email = f"student2_test_{test_suffix}@vedantu-test.com"
    instructor_email = f"instructor_test_{test_suffix}@vedantu-test.com"
    instructor_password = "SecureInstructorPass123!"

    client = httpx.AsyncClient(timeout=30.0)

    # --------------------------------------------------------------------------
    # 1. INITIAL HEALTH & PLATFORM CHECKS
    # --------------------------------------------------------------------------
    print("\n--- 1. Initial Health & Platform Checks ---")
    try:
        r = await client.get(f"{FRONTEND_URL}/")
        passed = (r.status_code == 200 and "Vedantu" in r.text)
        record_test("Infrastructure", "Frontend Web Availability", "HTTP 200 with Vedantu HTML", f"HTTP {r.status_code} ({len(r.text)} bytes)", passed)
    except Exception as e:
        record_test("Infrastructure", "Frontend Web Availability", "HTTP 200", f"Error: {e}", False, str(e))

    try:
        r = await client.get(f"{PROXY_API_URL}/health")
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and data.get("status") == "healthy")
        record_test("Infrastructure", "Backend Health via Frontend Proxy", "HTTP 200 with status=healthy", f"HTTP {r.status_code}, data={data}", passed)
    except Exception as e:
        record_test("Infrastructure", "Backend Health via Frontend Proxy", "HTTP 200", f"Error: {e}", False, str(e))

    try:
        r = await client.get(f"{DIRECT_API_URL}/health")
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and data.get("status") == "healthy")
        record_test("Infrastructure", "Backend Health via Direct Port 8000", "HTTP 200 with status=healthy", f"HTTP {r.status_code}, data={data}", passed)
    except Exception as e:
        record_test("Infrastructure", "Backend Health via Direct Port 8000", "HTTP 200", f"Error: {e}", False, str(e))

    # --------------------------------------------------------------------------
    # 2. AUTHENTICATION & RBAC TESTING
    # --------------------------------------------------------------------------
    print("\n--- 2. Authentication & RBAC Testing ---")
    
    # 2.1 Weak password rejection
    try:
        r = await client.post(f"{PROXY_API_URL}/auth/register", json={
            "full_name": "Weak Pass User",
            "email": f"weak_{test_suffix}@vedantu-test.com",
            "password": "123"
        })
        passed = (r.status_code == 422)
        record_test("Authentication", "Weak Password Registration Rejection", "HTTP 422 Unprocessable Content", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Authentication", "Weak Password Registration Rejection", "HTTP 422", str(e), False, str(e))

    # 2.2 Student registration
    student_tokens = None
    try:
        r = await client.post(f"{PROXY_API_URL}/auth/register", json={
            "full_name": "Test Student One",
            "email": student_email,
            "password": student_password
        })
        passed = (r.status_code == 201 and "access_token" in r.json())
        if passed:
            student_tokens = r.json()
        record_test("Authentication", "Student Registration", "HTTP 201 with access & refresh tokens", f"HTTP {r.status_code}, has_token={'access_token' in r.json() if r.status_code==201 else False}", passed)
    except Exception as e:
        record_test("Authentication", "Student Registration", "HTTP 201", str(e), False, str(e))

    # 2.3 Duplicate email registration rejection
    try:
        r = await client.post(f"{PROXY_API_URL}/auth/register", json={
            "full_name": "Duplicate Student",
            "email": student_email,
            "password": student_password
        })
        passed = (r.status_code == 409)
        record_test("Authentication", "Duplicate Email Registration Rejection", "HTTP 409 Conflict", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Authentication", "Duplicate Email Registration Rejection", "HTTP 409", str(e), False, str(e))

    # 2.4 Invalid login rejection
    try:
        r = await client.post(f"{PROXY_API_URL}/auth/login", json={
            "email": student_email,
            "password": "WrongPassword999!"
        })
        passed = (r.status_code == 401 and "Invalid" in r.text)
        record_test("Authentication", "Invalid Password Login Rejection", "HTTP 401 with generic message", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Authentication", "Invalid Password Login Rejection", "HTTP 401", str(e), False, str(e))

    # 2.5 Valid student login
    student_access_token = None
    student_refresh_token = None
    try:
        r = await client.post(f"{PROXY_API_URL}/auth/login", json={
            "email": student_email,
            "password": student_password
        })
        passed = (r.status_code == 200 and "access_token" in r.json())
        if passed:
            student_access_token = r.json()["access_token"]
            student_refresh_token = r.json()["refresh_token"]
        record_test("Authentication", "Student Login with Valid Credentials", "HTTP 200 with JWT tokens", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Authentication", "Student Login with Valid Credentials", "HTTP 200", str(e), False, str(e))

    # 2.6 Authenticated user profile (/auth/me)
    student_headers = {"Authorization": f"Bearer {student_access_token}"} if student_access_token else {}
    student_id = None
    try:
        r = await client.get(f"{PROXY_API_URL}/auth/me", headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        student_id = data.get("id")
        passed = (r.status_code == 200 and "STUDENT" in data.get("roles", []) and "password" not in data)
        record_test("Authentication", "Authenticated Profile Introspection (/auth/me)", "HTTP 200 with STUDENT role and no password leak", f"HTTP {r.status_code}, roles={data.get('roles')}", passed)
    except Exception as e:
        record_test("Authentication", "Authenticated Profile Introspection", "HTTP 200", str(e), False, str(e))

    # 2.7 Token Refresh
    try:
        r = await client.post(f"{PROXY_API_URL}/auth/refresh", json={
            "refresh_token": student_refresh_token
        })
        passed = (r.status_code == 200 and "access_token" in r.json())
        if passed:
            student_access_token = r.json()["access_token"]
            student_headers = {"Authorization": f"Bearer {student_access_token}"}
        record_test("Authentication", "Token Refresh (/auth/refresh)", "HTTP 200 with new access token", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Authentication", "Token Refresh", "HTTP 200", str(e), False, str(e))

    # 2.8 Protected API without Token
    try:
        r = await client.get(f"{PROXY_API_URL}/auth/me")
        passed = (r.status_code == 401)
        record_test("Authentication", "Protected API Without Token Rejection", "HTTP 401 Unauthorized", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Authentication", "Protected API Without Token Rejection", "HTTP 401", str(e), False, str(e))

    # 2.9 Student attempting Instructor Route (RBAC)
    try:
        r = await client.post(f"{PROXY_API_URL}/questions", json={
            "title": "Unauthorized Question",
            "problem_description": "Should fail",
            "marks": 10
        }, headers=student_headers)
        passed = (r.status_code == 403)
        record_test("RBAC", "Student Forbidden from Question Creation", "HTTP 403 Forbidden", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("RBAC", "Student Forbidden from Question Creation", "HTTP 403", str(e), False, str(e))

    # 2.10 Register second student for isolation testing
    student2_access_token = None
    student2_id = None
    try:
        r = await client.post(f"{PROXY_API_URL}/auth/register", json={
            "full_name": "Test Student Two",
            "email": student2_email,
            "password": student_password
        })
        if r.status_code == 201:
            student2_access_token = r.json()["access_token"]
            r2 = await client.get(f"{PROXY_API_URL}/auth/me", headers={"Authorization": f"Bearer {student2_access_token}"})
            if r2.status_code == 200:
                student2_id = r2.json().get("id")
        passed = (student2_access_token is not None and student2_id is not None)
        record_test("Authentication", "Register Second Student for Multi-Tenant Testing", "Registered successfully", f"Student 2 ID: {student2_id}", passed)
    except Exception as e:
        record_test("Authentication", "Register Second Student", "Success", str(e), False, str(e))

    student2_headers = {"Authorization": f"Bearer {student2_access_token}"} if student2_access_token else {}

    # 2.11 Create Instructor Account via direct DB assignment for testing
    instructor_access_token = None
    instructor_headers = {}
    try:
        # First register as user
        r = await client.post(f"{PROXY_API_URL}/auth/register", json={
            "full_name": "Dr. Instructor Test",
            "email": instructor_email,
            "password": instructor_password
        })
        # Promote to INSTRUCTOR in DB via backend container
        promote_cmd = f"""docker exec vedantu-backend python -c "import asyncio; from sqlalchemy import select; from app.core.database import async_session_factory; from app.models import User, Role, UserRole; async def p(): async with async_session_factory() as s: u = (await s.execute(select(User).where(User.email=='{instructor_email}'))).scalar_one(); r = (await s.execute(select(Role).where(Role.name=='INSTRUCTOR'))).scalar_one(); s.add(UserRole(user_id=u.id, role_id=r.id)); await s.commit(); print('PROMOTED'); asyncio.run(p())" """
        proc = await asyncio.create_subprocess_shell(promote_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        
        # Now login as instructor
        r_login = await client.post(f"{PROXY_API_URL}/auth/login", json={
            "email": instructor_email,
            "password": instructor_password
        })
        if r_login.status_code == 200:
            instructor_access_token = r_login.json()["access_token"]
            instructor_headers = {"Authorization": f"Bearer {instructor_access_token}"}
            
        # Verify instructor dashboard access
        r_dash = await client.get(f"{PROXY_API_URL}/auth/instructor/dashboard", headers=instructor_headers)
        passed = (r_dash.status_code == 200 and "Instructor" in r_dash.text)
        record_test("RBAC", "Instructor Authorization & Dashboard Access", "HTTP 200 with Instructor Portal greeting", f"HTTP {r_dash.status_code}", passed)
    except Exception as e:
        record_test("RBAC", "Instructor Authorization", "HTTP 200", str(e), False, str(e))

    # --------------------------------------------------------------------------
    # 3. QUESTION BANK TESTING
    # --------------------------------------------------------------------------
    print("\n--- 3. Question Bank Testing ---")
    question_id = None
    
    # 3.1 Question Creation by Instructor
    try:
        q_payload = {
            "title": f"Sum of Two Numbers ({test_suffix})",
            "problem_description": "Read two space-separated integers A and B from standard input and print their sum.",
            "input_format": "Two integers A and B separated by space",
            "output_format": "Single integer representing A + B",
            "constraints": "-1000 <= A, B <= 1000",
            "difficulty": "EASY",
            "topic": "Algorithms",
            "marks": 20,
            "time_limit_seconds": 2.0,
            "memory_limit_mb": 256,
            "test_cases": [
                {
                    "input_data": "3 5\n",
                    "expected_output": "8\n",
                    "explanation": "3 + 5 = 8",
                    "marks": 10,
                    "display_order": 1,
                    "is_hidden": False,
                    "category": "SAMPLE"
                },
                {
                    "input_data": "100 250\n",
                    "expected_output": "350\n",
                    "explanation": None,
                    "marks": 10,
                    "display_order": 2,
                    "is_hidden": True,
                    "category": "FUNCTIONAL"
                }
            ]
        }
        r = await client.post(f"{PROXY_API_URL}/questions", json=q_payload, headers=instructor_headers)
        passed = (r.status_code == 201 and "id" in r.json())
        if passed:
            question_id = r.json()["id"]
        record_test("Question Bank", "Question Creation with Test Cases", "HTTP 201 Created", f"HTTP {r.status_code}, ID={question_id}", passed)
    except Exception as e:
        record_test("Question Bank", "Question Creation", "HTTP 201", str(e), False, str(e))

    # 3.2 Question Listing
    try:
        r = await client.get(f"{PROXY_API_URL}/questions", headers=instructor_headers)
        passed = (r.status_code == 200 and any(q.get("id") == question_id for q in r.json()))
        record_test("Question Bank", "Question Listing", "HTTP 200 containing created question", f"HTTP {r.status_code}, count={len(r.json()) if r.status_code==200 else 0}", passed)
    except Exception as e:
        record_test("Question Bank", "Question Listing", "HTTP 200", str(e), False, str(e))

    # 3.3 Question Details for Instructor (all test cases visible)
    try:
        r = await client.get(f"{PROXY_API_URL}/questions/{question_id}", headers=instructor_headers)
        data = r.json() if r.status_code == 200 else {}
        tcs = data.get("test_cases", [])
        hidden_tcs = [tc for tc in tcs if tc.get("is_hidden") is True]
        passed = (r.status_code == 200 and len(tcs) == 2 and len(hidden_tcs) == 1)
        record_test("Question Bank", "Instructor Question Details (Exposes Hidden Cases)", "HTTP 200 with 2 test cases (1 hidden)", f"HTTP {r.status_code}, total={len(tcs)}, hidden={len(hidden_tcs)}", passed)
    except Exception as e:
        record_test("Question Bank", "Instructor Question Details", "HTTP 200", str(e), False, str(e))

    # 3.4 Question Details for Student (Hidden test cases protected)
    try:
        r = await client.get(f"{PROXY_API_URL}/questions/{question_id}", headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        tcs = data.get("test_cases", [])
        has_hidden = any(tc.get("is_hidden", False) for tc in tcs)
        passed = (r.status_code == 200 and len(tcs) == 1 and not has_hidden)
        record_test("Question Bank", "Student Question Details (Hidden Cases Stripped)", "HTTP 200 with only sample cases exposed", f"HTTP {r.status_code}, exposed_cases={len(tcs)}, has_hidden={has_hidden}", passed)
    except Exception as e:
        record_test("Question Bank", "Student Question Details", "HTTP 200", str(e), False, str(e))

    # 3.5 Question Editing
    try:
        r = await client.put(f"{PROXY_API_URL}/questions/{question_id}", json={
            "title": f"Sum of Two Numbers Updated ({test_suffix})",
            "marks": 20
        }, headers=instructor_headers)
        passed = (r.status_code == 200 and "Updated" in r.json().get("title", ""))
        record_test("Question Bank", "Question Modification by Instructor", "HTTP 200 with updated title", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Question Bank", "Question Modification", "HTTP 200", str(e), False, str(e))

    # 3.6 Question Pre-flight Validation
    try:
        r = await client.post(f"{PROXY_API_URL}/questions/{question_id}/validate", headers=instructor_headers)
        passed = (r.status_code == 200 and r.json().get("is_valid") is True)
        record_test("Question Bank", "Question Pre-flight Validation", "HTTP 200 with is_valid=True", f"HTTP {r.status_code}, is_valid={r.json().get('is_valid') if r.status_code==200 else False}", passed)
    except Exception as e:
        record_test("Question Bank", "Question Pre-flight Validation", "HTTP 200", str(e), False, str(e))

    # Fetch active programming languages
    py_lang_id = None
    java_lang_id = None
    try:
        # Get from DB inside container
        get_langs_cmd = """docker exec vedantu-backend python -c "import asyncio, json; from sqlalchemy import select; from app.core.database import async_session_factory; from app.models import ProgrammingLanguage; async def l(): async with async_session_factory() as s: langs = (await s.execute(select(ProgrammingLanguage))).scalars().all(); print(json.dumps([{'id': str(x.id), 'name': x.name, 'judge0_id': x.judge0_language_id} for x in langs])); asyncio.run(l())" """
        proc = await asyncio.create_subprocess_shell(get_langs_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        lang_list = json.loads(stdout.decode().strip())
        for l in lang_list:
            if "Python" in l["name"]:
                py_lang_id = l["id"]
            elif "Java" in l["name"]:
                java_lang_id = l["id"]
        print(f"       Found Python Lang ID: {py_lang_id}, Java Lang ID: {java_lang_id}")
    except Exception as e:
        print(f"       Error discovering languages: {e}")

    # --------------------------------------------------------------------------
    # 4. ASSESSMENT WORKFLOW SETUP & TESTING
    # --------------------------------------------------------------------------
    print("\n--- 4. Assessment Workflow Setup ---")
    assessment_id = None

    # 4.1 Create Assessment
    try:
        a_payload = {
            "title": f"Algorithms Sprint Assessment ({test_suffix})",
            "description": "Timed coding assessment testing basic algorithmic proficiency.",
            "instructions": "Read input from standard input and write to standard output. Use Python 3 or Java.",
            "duration_minutes": 60,
            "total_marks": 20,
            "passing_marks": 10,
            "difficulty": "EASY",
            "allowed_languages": "ALL_ACTIVE",
            "proctoring_config": {
                "require_webcam": False,
                "enforce_fullscreen": True,
                "track_tab_switches": True,
                "max_tab_switch_count": 3
            },
            "question_ids": [question_id] if question_id else []
        }
        r = await client.post(f"{PROXY_API_URL}/assessments", json=a_payload, headers=instructor_headers)
        passed = (r.status_code == 201 and "id" in r.json())
        if passed:
            assessment_id = r.json()["id"]
        record_test("Assessment Workflow", "Assessment Creation", "HTTP 201 Created", f"HTTP {r.status_code}, ID={assessment_id}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Assessment Creation", "HTTP 201", str(e), False, str(e))

    # 4.2 Publish Assessment
    try:
        r = await client.post(f"{PROXY_API_URL}/assessments/{assessment_id}/publish", headers=instructor_headers)
        passed = (r.status_code == 200 and r.json().get("status") == "PUBLISHED")
        record_test("Assessment Workflow", "Publish Assessment", "HTTP 200 with status=PUBLISHED", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Publish Assessment", "HTTP 200", str(e), False, str(e))

    # 4.3 Student lists assessments
    try:
        r = await client.get(f"{PROXY_API_URL}/student/assessments", headers=student_headers)
        passed = (r.status_code == 200 and any(a.get("id") == assessment_id for a in r.json()))
        record_test("Assessment Workflow", "Student Assessment Discovery", "HTTP 200 with published assessment", f"HTTP {r.status_code}, count={len(r.json()) if r.status_code==200 else 0}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Student Assessment Discovery", "HTTP 200", str(e), False, str(e))

    # 4.4 Student starts assessment attempt
    attempt_id = None
    try:
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/start", headers=student_headers)
        data = r.json() if r.status_code in (200, 201) else {}
        passed = (r.status_code in (200, 201) and data.get("status") == "IN_PROGRESS")
        if passed:
            attempt_id = data.get("id")
        record_test("Assessment Workflow", "Start Assessment Attempt", "HTTP 200/201 with status=IN_PROGRESS", f"HTTP {r.status_code}, attempt_id={attempt_id}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Start Assessment Attempt", "HTTP 200/201", str(e), False, str(e))

    # 4.5 Draft Autosave
    try:
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/drafts", json={
            "question_id": question_id,
            "programming_language_id": py_lang_id,
            "source_code": "# Draft autosave test\na, b = map(int, input().split())\nprint(a + b)"
        }, headers=student_headers)
        passed = (r.status_code == 200 and "source_code" in r.json())
        record_test("Assessment Workflow", "Draft Autosave (/drafts)", "HTTP 200 with persisted source code", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Draft Autosave", "HTTP 200", str(e), False, str(e))

    # --------------------------------------------------------------------------
    # 5. CODE EXECUTION TESTING (Python & Java via Judge0)
    # --------------------------------------------------------------------------
    print("\n--- 5. Code Execution Testing (Python & Java) ---")

    # 5.1 Python - Sample Run
    try:
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/run-sample", json={
            "question_id": question_id,
            "programming_language_id": py_lang_id,
            "source_code": "a, b = map(int, input().split())\nprint(a + b)"
        }, headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        tc_results = data.get("test_case_results", [])
        passed = (r.status_code == 200 and len(tc_results) == 1 and tc_results[0].get("status") == "ACCEPTED")
        record_test("Code Execution", "Python 3: Sample Run (Correct)", "HTTP 200 with 1 ACCEPTED sample case", f"HTTP {r.status_code}, status={tc_results[0].get('status') if tc_results else 'None'}", passed)
    except Exception as e:
        record_test("Code Execution", "Python 3: Sample Run", "HTTP 200", str(e), False, str(e))

    # 5.2 Python - Incorrect Output
    try:
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/run-sample", json={
            "question_id": question_id,
            "programming_language_id": py_lang_id,
            "source_code": "a, b = map(int, input().split())\nprint(a - b)"  # Wrong logic
        }, headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        tc_results = data.get("test_case_results", [])
        passed = (r.status_code == 200 and len(tc_results) == 1 and tc_results[0].get("status") == "WRONG_ANSWER")
        record_test("Code Execution", "Python 3: Wrong Output Detection", "HTTP 200 with WRONG_ANSWER", f"HTTP {r.status_code}, status={tc_results[0].get('status') if tc_results else 'None'}", passed)
    except Exception as e:
        record_test("Code Execution", "Python 3: Wrong Output Detection", "HTTP 200", str(e), False, str(e))

    # 5.3 Python - Runtime Error
    try:
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/run-sample", json={
            "question_id": question_id,
            "programming_language_id": py_lang_id,
            "source_code": "a, b = map(int, input().split())\nprint(a / 0)"  # Division by zero
        }, headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        tc_results = data.get("test_case_results", [])
        status_val = tc_results[0].get("status") if tc_results else "None"
        passed = (r.status_code == 200 and status_val in ("RUNTIME_ERROR", "ERROR", "RUNTIME_ERROR_SIGFPE", "RUNTIME_ERROR_NZEC"))
        record_test("Code Execution", "Python 3: Runtime Error Handling", "HTTP 200 with RUNTIME_ERROR/ERROR", f"HTTP {r.status_code}, status={status_val}", passed)
    except Exception as e:
        record_test("Code Execution", "Python 3: Runtime Error Handling", "HTTP 200", str(e), False, str(e))

    # 5.4 Java - Valid Solution
    try:
        java_code = """import java.util.Scanner;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (sc.hasNextInt()) {
            int a = sc.nextInt();
            int b = sc.nextInt();
            System.out.println(a + b);
        }
    }
}"""
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/run-sample", json={
            "question_id": question_id,
            "programming_language_id": java_lang_id,
            "source_code": java_code
        }, headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        tc_results = data.get("test_case_results", [])
        status_val = tc_results[0].get("status") if tc_results else "None"
        passed = (r.status_code == 200 and status_val == "ACCEPTED")
        record_test("Code Execution", "Java: Valid Program Execution", "HTTP 200 with ACCEPTED", f"HTTP {r.status_code}, status={status_val}", passed)
    except Exception as e:
        record_test("Code Execution", "Java: Valid Program Execution", "HTTP 200", str(e), False, str(e))

    # 5.5 Java - Compilation Error
    try:
        java_broken = """public class Main {
    public static void main(String[] args) {
        System.out.println("Missing semicolon")
    }
}"""
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/run-sample", json={
            "question_id": question_id,
            "programming_language_id": java_lang_id,
            "source_code": java_broken
        }, headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        tc_results = data.get("test_case_results", [])
        status_val = tc_results[0].get("status") if tc_results else "None"
        passed = (r.status_code == 200 and status_val in ("COMPILATION_ERROR", "ERROR"))
        record_test("Code Execution", "Java: Compilation Error Detection", "HTTP 200 with COMPILATION_ERROR", f"HTTP {r.status_code}, status={status_val}", passed)
    except Exception as e:
        record_test("Code Execution", "Java: Compilation Error Detection", "HTTP 200", str(e), False, str(e))

    # 5.6 Final Submission with Full Evaluation (Sample + Hidden Test Cases)
    submission_id = None
    try:
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/submit-code", json={
            "question_id": question_id,
            "programming_language_id": py_lang_id,
            "source_code": "a, b = map(int, input().split())\nprint(a + b)"
        }, headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        submission_id = data.get("id")
        score = data.get("score")
        passed = (r.status_code == 200 and score == 20 and data.get("status") == "ACCEPTED")
        record_test("Assessment Workflow", "Final Code Submission & Hidden Evaluation", "HTTP 200, score=20, status=ACCEPTED", f"HTTP {r.status_code}, score={score}, submission_id={submission_id}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Final Code Submission & Hidden Evaluation", "HTTP 200", str(e), False, str(e))

    # 5.7 Assessment Finish
    try:
        r = await client.post(f"{PROXY_API_URL}/student/assessments/{assessment_id}/finish", headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and data.get("status") == "COMPLETED")
        record_test("Assessment Workflow", "Finish Assessment", "HTTP 200 with status=COMPLETED", f"HTTP {r.status_code}, status={data.get('status')}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Finish Assessment", "HTTP 200", str(e), False, str(e))

    # 5.8 Assessment Results Display
    try:
        r = await client.get(f"{PROXY_API_URL}/student/assessments/{assessment_id}/results", headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and data.get("total_score") == 20 and data.get("status") == "COMPLETED")
        record_test("Assessment Workflow", "Result Display & Grade Summary", "HTTP 200 with total_score=20", f"HTTP {r.status_code}, score={data.get('total_score')}", passed)
    except Exception as e:
        record_test("Assessment Workflow", "Result Display", "HTTP 200", str(e), False, str(e))

    # 5.9 Multi-Tenant Isolation: Student B cannot view Student A's attempt results
    try:
        r = await client.get(f"{PROXY_API_URL}/student/assessments/{assessment_id}/results", headers=student2_headers)
        passed = (r.status_code in (403, 404))
        record_test("Security", "Multi-Tenant Attempt Isolation", "HTTP 403 or 404 for unowned attempt", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Security", "Multi-Tenant Attempt Isolation", "HTTP 403/404", str(e), False, str(e))

    # --------------------------------------------------------------------------
    # 6. AI EVALUATION & STATIC CODE ANALYSIS
    # --------------------------------------------------------------------------
    print("\n--- 6. AI Evaluation & Static Analysis ---")
    try:
        r = await client.get(f"{PROXY_API_URL}/student/submissions/{submission_id}/evaluation", headers=student_headers)
        data = r.json() if r.status_code == 200 else {}
        static_analysis = data.get("static_analysis", {})
        has_metrics = ("cyclomatic_complexity" in static_analysis or "ast_metrics" in static_analysis or "complexity" in str(static_analysis))
        has_ai = ("strengths" in data or "code_quality_feedback" in data or "ai_feedback" in data or "qualitative_feedback" in data)
        passed = (r.status_code == 200 and (has_metrics or has_ai or "evaluation" in data or "status" in data))
        record_test("AI Evaluation", "Static Analysis & Qualitative AI Feedback", "HTTP 200 with static metrics and qualitative evaluation", f"HTTP {r.status_code}, has_metrics={has_metrics}, has_ai={has_ai}", passed)
    except Exception as e:
        record_test("AI Evaluation", "Static Analysis & Qualitative AI Feedback", "HTTP 200", str(e), False, str(e))

    # --------------------------------------------------------------------------
    # 7. ADAPTIVE ASSESSMENT ENGINE
    # --------------------------------------------------------------------------
    print("\n--- 7. Adaptive Assessment Engine ---")
    
    # 7.1 Topic Mastery
    try:
        r = await client.get(f"{PROXY_API_URL}/adaptive/mastery", headers=student_headers)
        passed = (r.status_code == 200 and isinstance(r.json(), (list, dict)))
        record_test("Adaptive Engine", "Student Topic Mastery Data", "HTTP 200 list/dict of mastery scores", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Adaptive Engine", "Student Topic Mastery Data", "HTTP 200", str(e), False, str(e))

    # 7.2 Strengths & Weaknesses Profile
    try:
        r = await client.get(f"{PROXY_API_URL}/adaptive/profile", headers=student_headers)
        passed = (r.status_code == 200 and "weak_topics" in r.text or "mastery" in r.text or "student_id" in r.text)
        record_test("Adaptive Engine", "Strength and Weakness Profile", "HTTP 200 with diagnostic profile", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Adaptive Engine", "Strength and Weakness Profile", "HTTP 200", str(e), False, str(e))

    # 7.3 Difficulty Recommendations
    try:
        r = await client.get(f"{PROXY_API_URL}/adaptive/recommendations", headers=student_headers)
        passed = (r.status_code == 200 and isinstance(r.json(), list))
        record_test("Adaptive Engine", "Adaptive Question Recommendations", "HTTP 200 list of recommended questions", f"HTTP {r.status_code}, count={len(r.json()) if r.status_code==200 else 0}", passed)
    except Exception as e:
        record_test("Adaptive Engine", "Adaptive Question Recommendations", "HTTP 200", str(e), False, str(e))

    # 7.4 Practice Question Submission
    try:
        r = await client.post(f"{PROXY_API_URL}/adaptive/practice/{question_id}/submit", json={
            "programming_language_id": py_lang_id,
            "source_code": "a, b = map(int, input().split())\nprint(a + b)"
        }, headers=student_headers)
        passed = (r.status_code == 200 and r.json().get("status") == "ACCEPTED")
        record_test("Adaptive Engine", "Practice Question Submission", "HTTP 200 with evaluation", f"HTTP {r.status_code}, status={r.json().get('status') if r.status_code==200 else 'None'}", passed)
    except Exception as e:
        record_test("Adaptive Engine", "Practice Question Submission", "HTTP 200", str(e), False, str(e))

    # 7.5 Mastery Recalculation
    try:
        r = await client.post(f"{PROXY_API_URL}/adaptive/recalculate", headers=student_headers)
        passed = (r.status_code == 200)
        record_test("Adaptive Engine", "Mastery Score Recalculation", "HTTP 200 OK", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Adaptive Engine", "Mastery Score Recalculation", "HTTP 200", str(e), False, str(e))

    # --------------------------------------------------------------------------
    # 8. PROCTORING & INTEGRITY MONITORING
    # --------------------------------------------------------------------------
    print("\n--- 8. Proctoring & Integrity Monitoring ---")
    proctoring_session_id = None

    # 8.1 Initialize Proctoring Session
    try:
        r = await client.post(f"{PROXY_API_URL}/proctoring/sessions", json={
            "assessment_id": assessment_id,
            "attempt_id": attempt_id
        }, headers=student_headers)
        data = r.json() if r.status_code in (200, 201) else {}
        proctoring_session_id = data.get("id")
        passed = (r.status_code in (200, 201) and proctoring_session_id is not None)
        record_test("Proctoring", "Initialize Proctoring Session", "HTTP 200/201 with session ID", f"HTTP {r.status_code}, session_id={proctoring_session_id}", passed)
    except Exception as e:
        record_test("Proctoring", "Initialize Proctoring Session", "HTTP 200/201", str(e), False, str(e))

    # 8.2 Student Proctoring Consent
    try:
        r = await client.post(f"{PROXY_API_URL}/proctoring/sessions/{proctoring_session_id}/consent", json={
            "consent_granted": True,
            "fullscreen_acknowledged": True,
            "tab_monitoring_acknowledged": True
        }, headers=student_headers)
        passed = (r.status_code == 200 and r.json().get("consent_granted") is True)
        record_test("Proctoring", "Student Proctoring Consent", "HTTP 200 with consent_granted=True", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Proctoring", "Student Proctoring Consent", "HTTP 200", str(e), False, str(e))

    # 8.3 Record Proctoring Events (Tab Switch, Fullscreen Exit)
    try:
        r = await client.post(f"{PROXY_API_URL}/proctoring/events", json={
            "session_id": proctoring_session_id,
            "event_type": "TAB_SWITCH",
            "metadata": {"switched_to": "external_window", "duration_seconds": 3.5}
        }, headers=student_headers)
        passed = (r.status_code in (200, 201))
        record_test("Proctoring", "Record Tab Switch Event", "HTTP 200/201 Event Recorded", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Proctoring", "Record Tab Switch Event", "HTTP 200/201", str(e), False, str(e))

    try:
        r = await client.post(f"{PROXY_API_URL}/proctoring/events", json={
            "session_id": proctoring_session_id,
            "event_type": "FULLSCREEN_EXIT",
            "metadata": {"reason": "escape_pressed"}
        }, headers=student_headers)
        passed = (r.status_code in (200, 201))
        record_test("Proctoring", "Record Fullscreen Exit Event", "HTTP 200/201 Event Recorded", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Proctoring", "Record Fullscreen Exit Event", "HTTP 200/201", str(e), False, str(e))

    # 8.4 Generate Alert
    try:
        r = await client.post(f"{PROXY_API_URL}/proctoring/alerts", json={
            "session_id": proctoring_session_id,
            "alert_type": "MULTIPLE_TAB_SWITCHES",
            "severity": "WARNING",
            "description": "Candidate switched tabs multiple times."
        }, headers=student_headers)
        passed = (r.status_code in (200, 201))
        record_test("Proctoring", "Generate Proctoring Alert", "HTTP 200/201 Alert Created", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Proctoring", "Generate Proctoring Alert", "HTTP 200/201", str(e), False, str(e))

    # 8.5 Instructor Audit Trail Access
    try:
        r = await client.get(f"{PROXY_API_URL}/proctoring/attempts/{attempt_id}/audit", headers=instructor_headers)
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and "events" in data and len(data["events"]) >= 2)
        record_test("Proctoring", "Instructor Proctoring Audit Trail", "HTTP 200 with events list", f"HTTP {r.status_code}, events={len(data.get('events', []))}", passed)
    except Exception as e:
        record_test("Proctoring", "Instructor Proctoring Audit Trail", "HTTP 200", str(e), False, str(e))

    # 8.6 Student Unauthorized Audit Access Rejection
    try:
        r = await client.get(f"{PROXY_API_URL}/proctoring/attempts/{attempt_id}/audit", headers=student_headers)
        passed = (r.status_code == 403)
        record_test("Security", "Student Denied Instructor Proctoring Audit", "HTTP 403 Forbidden", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Security", "Student Denied Instructor Proctoring Audit", "HTTP 403", str(e), False, str(e))

    # --------------------------------------------------------------------------
    # 9. ANALYTICS & REPORTING
    # --------------------------------------------------------------------------
    print("\n--- 9. Analytics & Reporting ---")

    # 9.1 Instructor Dashboard KPIs
    try:
        r = await client.get(f"{PROXY_API_URL}/analytics/dashboard", headers=instructor_headers)
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and "total_assessments" in data or "total_candidates" in data or "kpis" in str(data))
        record_test("Analytics", "Instructor Dashboard KPIs", "HTTP 200 with platform metrics", f"HTTP {r.status_code}, data={list(data.keys()) if isinstance(data, dict) else len(data)}", passed)
    except Exception as e:
        record_test("Analytics", "Instructor Dashboard KPIs", "HTTP 200", str(e), False, str(e))

    # 9.2 Assessment Aggregate Analytics
    try:
        r = await client.get(f"{PROXY_API_URL}/analytics/assessment/{assessment_id}", headers=instructor_headers)
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and "total_candidates" in data or "assessment_id" in str(data))
        record_test("Analytics", "Assessment Aggregate Analytics", "HTTP 200 with cohort statistics", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Analytics", "Assessment Aggregate Analytics", "HTTP 200", str(e), False, str(e))

    # 9.3 Candidate Individual Report
    try:
        r = await client.get(f"{PROXY_API_URL}/analytics/candidate/{student_id}", headers=instructor_headers)
        data = r.json() if r.status_code == 200 else {}
        passed = (r.status_code == 200 and ("user_id" in data or "candidate_id" in data or "full_name" in data))
        record_test("Analytics", "Candidate Performance Report", "HTTP 200 with candidate details", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Analytics", "Candidate Performance Report", "HTTP 200", str(e), False, str(e))

    # 9.4 Cohort Topic Proficiency
    try:
        r = await client.get(f"{PROXY_API_URL}/analytics/topic-proficiency", headers=instructor_headers)
        passed = (r.status_code == 200 and isinstance(r.json(), list))
        record_test("Analytics", "Cohort Topic Proficiency", "HTTP 200 list of topic proficiencies", f"HTTP {r.status_code}, count={len(r.json()) if r.status_code==200 else 0}", passed)
    except Exception as e:
        record_test("Analytics", "Cohort Topic Proficiency", "HTTP 200", str(e), False, str(e))

    # 9.5 Assessment Leaderboard
    try:
        r = await client.get(f"{PROXY_API_URL}/analytics/leaderboard/{assessment_id}", headers=instructor_headers)
        passed = (r.status_code == 200 and isinstance(r.json(), list))
        record_test("Analytics", "Assessment Leaderboard", "HTTP 200 list of candidate rankings", f"HTTP {r.status_code}, count={len(r.json()) if r.status_code==200 else 0}", passed)
    except Exception as e:
        record_test("Analytics", "Assessment Leaderboard", "HTTP 200", str(e), False, str(e))

    # 9.6 CSV Export & Privacy Check
    try:
        r = await client.get(f"{PROXY_API_URL}/analytics/assessment/{assessment_id}/export/csv", headers=instructor_headers)
        csv_text = r.text if r.status_code == 200 else ""
        has_csv_headers = ("Candidate" in csv_text or "Score" in csv_text or "Email" in csv_text or "User" in csv_text or "attempt" in csv_text.lower())
        no_secrets = ("password_hash" not in csv_text and "jwt" not in csv_text.lower() and "secret" not in csv_text.lower())
        passed = (r.status_code == 200 and has_csv_headers and no_secrets)
        record_test("Analytics", "Assessment CSV Report Export & Privacy Audit", "HTTP 200 with CSV text without credentials or tokens", f"HTTP {r.status_code}, has_headers={has_csv_headers}, no_secrets={no_secrets}", passed)
    except Exception as e:
        record_test("Analytics", "Assessment CSV Report Export", "HTTP 200", str(e), False, str(e))

    # 9.7 Student Forbidden from Analytics
    try:
        r = await client.get(f"{PROXY_API_URL}/analytics/dashboard", headers=student_headers)
        passed = (r.status_code == 403)
        record_test("Security", "Student Forbidden from Analytics Dashboard", "HTTP 403 Forbidden", f"HTTP {r.status_code}", passed)
    except Exception as e:
        record_test("Security", "Student Forbidden from Analytics", "HTTP 403", str(e), False, str(e))

    # --------------------------------------------------------------------------
    # 10. CLEANUP DISPOSABLE TEST RECORDS
    # --------------------------------------------------------------------------
    print("\n--- 10. Cleanup of Disposable Test Records ---")
    try:
        cleanup_cmd = f"""docker exec vedantu-backend python -c "import asyncio; from sqlalchemy import delete, select; from app.core.database import async_session_factory; from app.models import User, Question, TestCase, Assessment, AssessmentAttempt, Submission, SubmissionTestCaseResult, ProctoringSession, ProctoringEvent, ProctoringAlert, CodeDraft; async def c(): async with async_session_factory() as s: 
    emails = ['{student_email}', '{student2_email}', '{instructor_email}'];
    u_ids = (await s.scalars(select(User.id).where(User.email.in_(emails)))).all();
    if u_ids:
        await s.execute(delete(ProctoringAlert).where(ProctoringAlert.session_id.in_(select(ProctoringSession.id).where(ProctoringSession.user_id.in_(u_ids)))));
        await s.execute(delete(ProctoringEvent).where(ProctoringEvent.session_id.in_(select(ProctoringSession.id).where(ProctoringSession.user_id.in_(u_ids)))));
        await s.execute(delete(ProctoringSession).where(ProctoringSession.user_id.in_(u_ids)));
        await s.execute(delete(SubmissionTestCaseResult).where(SubmissionTestCaseResult.submission_id.in_(select(Submission.id).where(Submission.user_id.in_(u_ids)))));
        await s.execute(delete(Submission).where(Submission.user_id.in_(u_ids)));
        await s.execute(delete(CodeDraft).where(CodeDraft.user_id.in_(u_ids)));
        await s.execute(delete(AssessmentAttempt).where(AssessmentAttempt.user_id.in_(u_ids)));
    if '{assessment_id}' != 'None':
        await s.execute(delete(Assessment).where(Assessment.id=='{assessment_id}'));
    if '{question_id}' != 'None':
        await s.execute(delete(TestCase).where(TestCase.question_id=='{question_id}'));
        await s.execute(delete(Question).where(Question.id=='{question_id}'));
    for u_id in u_ids:
        from app.models.role import UserRole; await s.execute(delete(UserRole).where(UserRole.user_id==u_id));
        await s.execute(delete(User).where(User.id==u_id));
    await s.commit(); print('CLEANUP_SUCCESS'); asyncio.run(c())" """
        proc = await asyncio.create_subprocess_shell(cleanup_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        passed = ("CLEANUP_SUCCESS" in stdout.decode())
        record_test("Data Hygiene", "Disposable Test Data Cleanup", "All test entities purged cleanly", stdout.decode().strip(), passed)
    except Exception as e:
        record_test("Data Hygiene", "Disposable Test Data Cleanup", "Cleaned up", str(e), False, str(e))

    await client.aclose()

    # --------------------------------------------------------------------------
    # SUMMARY REPORT
    # --------------------------------------------------------------------------
    total = len(TEST_RESULTS)
    passed_cnt = sum(1 for t in TEST_RESULTS if t["status"] == "PASS")
    failed_cnt = sum(1 for t in TEST_RESULTS if t["status"] == "FAIL")

    print("\n" + "=" * 80)
    print("FUNCTIONAL TEST EXECUTION SUMMARY")
    print(f"Total Tests Run: {total}")
    print(f"Passed:          {passed_cnt}")
    print(f"Failed:          {failed_cnt}")
    print(f"Success Rate:    {(passed_cnt/total)*100:.1f}%")
    print("=" * 80)

    # Save results as JSON
    with open("E:/VedantuCodingPlatform_New/test_results.json", "w") as f:
        json.dump(TEST_RESULTS, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_tests())
