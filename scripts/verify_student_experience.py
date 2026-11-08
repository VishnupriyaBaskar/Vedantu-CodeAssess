r"""
Comprehensive Student Experience Verification Script
Project: Vedantu Online Coding Assessment Platform
Workspace: E:\VedantuCodingPlatform_New

Verifies:
1. Topic browsing and syllabus catalog across 18 topics.
2. Full problem solving journey for 5 diverse topics (Arrays, Basic Mathematics, Strings, Graphs, Dynamic Programming):
   - Open topic details
   - Retrieve problem statement and public sample cases
   - Execute Run Sample in Judge0 sandbox
   - Submit Solution against hidden test cases
   - Validate real-time topic mastery recalculation
3. Assessment examination mode:
   - List non-empty published assessments
   - Start exam attempt
   - Run sample code
   - Submit solution
   - Finalize attempt and receive authoritative scorecard
"""

import asyncio
import json
import logging
import sys
import uuid
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_student_experience")

BASE_URL = "http://localhost:3000/api/v1"


async def main():
    logger.info("Initializing student experience verification against %s...", BASE_URL)
    results = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Register or Login a fresh test student
        test_email = f"student_journey_{uuid.uuid4().hex[:8]}@vedantu-test.com"
        password = "SecureStudentPass!123"

        reg_resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "full_name": "Test Student",
                "email": test_email,
                "password": password,
            },
        )
        if reg_resp.status_code == 201:
            tokens = reg_resp.json()
            access_token = tokens["access_token"]
            logger.info("Created and authenticated test student: %s", test_email)
        else:
            logger.warning("Registration response: %s %s", reg_resp.status_code, reg_resp.text)
            # Fallback to login
            login_resp = await client.post(
                f"{BASE_URL}/auth/login",
                json={"email": test_email, "password": password},
            )
            tokens = login_resp.json()
            access_token = tokens["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}

        # Fetch languages
        lang_res = await client.get(f"{BASE_URL}/student/languages", headers=headers)
        languages = lang_res.json()
        python_lang = next(l for l in languages if "python" in l["name"].lower())
        logger.info("Active Python runtime ID: %s", python_lang["id"])

        # =====================================================================
        # TEST 1: Topic Catalog Discovery
        # =====================================================================
        cat_res = await client.get(f"{BASE_URL}/adaptive/topics", headers=headers)
        assert cat_res.status_code == 200, f"Failed catalog: {cat_res.text}"
        cat_data = cat_res.json()
        catalog_topics = {t["topic"]: t for t in cat_data["topics"]}
        logger.info("Total topics in catalog: %d", len(catalog_topics))
        results["catalog_discovery"] = {
            "status": "PASSED",
            "total_topics": len(catalog_topics),
        }

        # =====================================================================
        # TEST 2: Verify 5 Required Topics
        # =====================================================================
        target_topics = [
            "Arrays",
            "Basic Mathematics",
            "Strings",
            "Graphs",
            "Dynamic Programming",
        ]

        topic_verifications = {}

        for topic in target_topics:
            logger.info("--- Testing Topic Practice Journey: %s ---", topic)
            # 1. Open topic
            detail_res = await client.get(
                f"{BASE_URL}/adaptive/topics/{topic}", headers=headers
            )
            assert detail_res.status_code == 200, f"Failed topic {topic}: {detail_res.text}"
            detail = detail_res.json()
            assert len(detail["questions"]) >= 3, f"Expected >=3 questions for {topic}"
            logger.info("  %s has %d questions, Recommended: %s", topic, len(detail["questions"]), detail["recommended_question"]["title"] if detail["recommended_question"] else None)

            # Pick a verified question with executable starter code (preferably from seed catalog)
            target_q = next(
                (q for q in detail["questions"] if "solve" in (q.get("starter_code") or "") or "reverseWords" in (q.get("starter_code") or "")),
                detail.get("recommended_question") or detail["questions"][0]
            )
            q_id = target_q["id"]

            # 2. Open problem statement
            q_res = await client.get(f"{BASE_URL}/adaptive/practice/{q_id}", headers=headers)
            assert q_res.status_code == 200, f"Failed question {q_id}: {q_res.text}"
            q_data = q_res.json()
            assert len(q_data["sample_test_cases"]) >= 1, "Missing sample test cases"
            logger.info("  Fetched problem: '%s' (%d sample test cases)", q_data["title"], len(q_data["sample_test_cases"]))

            # 3. Run Sample Code
            sample_res = await client.post(
                f"{BASE_URL}/adaptive/practice/{q_id}/run-sample",
                headers=headers,
                json={
                    "programming_language_id": python_lang["id"],
                    "source_code": target_q["starter_code"] or "print('ok')",
                },
            )
            assert sample_res.status_code == 200, f"Sample run failed: {sample_res.text}"
            sample_eval = sample_res.json()
            assert sample_eval["status"] == "ACCEPTED", f"Sample run status not ACCEPTED: {sample_eval['status']}"
            logger.info("  Run Sample: ACCEPTED (%d/%d sample cases passed)", sample_eval["passed_test_cases"], sample_eval["total_test_cases"])

            # 4. Submit Solution
            sub_res = await client.post(
                f"{BASE_URL}/adaptive/practice/{q_id}/submit",
                headers=headers,
                json={
                    "programming_language_id": python_lang["id"],
                    "source_code": target_q["starter_code"] or "print('ok')",
                },
            )
            assert sub_res.status_code == 200, f"Submission failed: {sub_res.text}"
            sub_eval = sub_res.json()
            assert sub_eval["status"] == "ACCEPTED", f"Submission status not ACCEPTED: {sub_eval['status']}"
            logger.info("  Submit Solution: ACCEPTED (%d/%d total cases passed)", sub_eval["passed_test_cases"], sub_eval["total_test_cases"])

            # 5. Verify Topic Details updated
            updated_detail_res = await client.get(
                f"{BASE_URL}/adaptive/topics/{topic}", headers=headers
            )
            updated_detail = updated_detail_res.json()
            updated_q = next(q for q in updated_detail["questions"] if q["id"] == q_id)
            assert updated_q["is_solved"] is True, "Question should now be marked solved"
            assert updated_detail["questions_solved"] >= 1, "Questions solved count should be >= 1"
            assert updated_detail["mastery_score"] > 0, "Mastery score should be updated"
            logger.info("  Real-time Mastery Updated: %s%% (Solved: %d)", updated_detail["mastery_score"], updated_detail["questions_solved"])

            topic_verifications[topic] = {
                "status": "PASSED",
                "question_title": q_data["title"],
                "sample_passed": sample_eval["passed_test_cases"],
                "total_passed": sub_eval["passed_test_cases"],
                "updated_mastery": updated_detail["mastery_score"],
            }

        results["topic_practice_journeys"] = topic_verifications

        # =====================================================================
        # TEST 3: Timed Assessment Mode Journey
        # =====================================================================
        logger.info("--- Testing Timed Examination Assessment Mode ---")
        assess_list_res = await client.get(f"{BASE_URL}/student/assessments", headers=headers)
        assert assess_list_res.status_code == 200, f"Failed listing assessments: {assess_list_res.text}"
        assessments = assess_list_res.json()
        assert len(assessments) > 0, "No assessments available for student"

        # Verify no 0-question assessments appear
        for a in assessments:
            assert a["question_count"] > 0, f"Assessment {a['title']} has 0 questions!"

        # Pick flagship assessment or first valid
        flagship = next((a for a in assessments if "core dsa" in a["title"].lower()), assessments[0])
        exam_id = flagship["id"]
        logger.info("Selected Assessment for Exam: '%s' (%d questions)", flagship["title"], flagship["question_count"])

        # Start exam
        start_res = await client.post(f"{BASE_URL}/student/assessments/{exam_id}/start", headers=headers)
        assert start_res.status_code == 200, f"Failed starting exam: {start_res.text}"
        exam_data = start_res.json()
        assert len(exam_data["questions"]) > 0, "Exam questions list is empty"
        first_exam_q = exam_data["questions"][0]
        assert len(first_exam_q["sample_test_cases"]) > 0, "Exam question missing sample test cases"
        logger.info("Started Assessment. First Question: '%s' (Samples: %d)", first_exam_q["title"], len(first_exam_q["sample_test_cases"]))

        # Execute Run Sample in Assessment
        exam_code = first_exam_q.get("starter_code") or (
            "import sys\n"
            "def solve():\n"
            "    tokens = sys.stdin.read().split()\n"
            "    if not tokens: return\n"
            "    n, t = int(tokens[0]), int(tokens[1])\n"
            "    arr = [int(tokens[i]) for i in range(2, 2 + n)]\n"
            "    s = set()\n"
            "    for x in arr:\n"
            "        if (t - x) in s:\n"
            "            print('YES')\n"
            "            return\n"
            "        s.add(x)\n"
            "    print('NO')\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        )
        exam_sample_res = await client.post(
            f"{BASE_URL}/student/assessments/{exam_id}/run-sample",
            headers=headers,
            json={
                "question_id": first_exam_q["id"],
                "programming_language_id": python_lang["id"],
                "source_code": exam_code,
            },
        )
        assert exam_sample_res.status_code == 200, f"Exam run-sample failed: {exam_sample_res.text}"
        exam_sample_eval = exam_sample_res.json()
        logger.info("Assessment Run Sample Status: %s (%d/%d)", exam_sample_eval["status"], exam_sample_eval["passed_test_cases"], exam_sample_eval["total_test_cases"])

        # Submit Question in Assessment
        exam_submit_res = await client.post(
            f"{BASE_URL}/student/assessments/{exam_id}/submit-code",
            headers=headers,
            json={
                "question_id": first_exam_q["id"],
                "programming_language_id": python_lang["id"],
                "source_code": exam_code,
            },
        )
        assert exam_submit_res.status_code == 200, f"Exam submit-code failed: {exam_submit_res.text}"
        exam_sub_eval = exam_submit_res.json()
        logger.info("Assessment Submit Code Status: %s (%d/%d)", exam_sub_eval["status"], exam_sub_eval["passed_test_cases"], exam_sub_eval["total_test_cases"])

        # Finish Assessment
        finish_res = await client.post(f"{BASE_URL}/student/assessments/{exam_id}/finish", headers=headers)
        assert finish_res.status_code == 200, f"Exam finish failed: {finish_res.text}"
        scorecard = finish_res.json()
        logger.info("Assessment Final Scorecard: Passed=%s, Score=%.1f/%.1f (%.1f%%)", scorecard["is_passed"], scorecard["total_score"], scorecard["total_possible_marks"], scorecard["percentage"])

        results["assessment_examination_mode"] = {
            "status": "PASSED",
            "assessment_title": flagship["title"],
            "score": scorecard["total_score"],
            "total_marks": scorecard["total_possible_marks"],
            "percentage": scorecard["percentage"],
            "is_passed": scorecard["is_passed"],
        }

    with open("student_experience_results.json", "w") as f:
        json.dump(results, f, indent=2)

    logger.info("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
