"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  addTestCaseApi,
  archiveQuestionApi,
  createQuestionApi,
  deleteTestCaseApi,
  listQuestionsApi,
  updateTestCaseApi,
  validateQuestionApi,
} from "@/lib/api/assessment";
import {
  DifficultyLevel,
  QuestionAdmin,
  QuestionCreatePayload,
  QuestionValidationResponse,
  TestCaseAdmin,
  TestCaseCategory,
} from "@/types/assessment";

export function QuestionBankSection() {
  const [questions, setQuestions] = useState<QuestionAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterDifficulty, setFilterDifficulty] = useState<string>("");
  const [filterTopic, setFilterTopic] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Create form modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Pre-flight Validation State
  const [validatingQuestionId, setValidatingQuestionId] = useState<string | null>(null);
  const [validationResult, setValidationResult] = useState<QuestionValidationResponse | null>(null);

  // Test Case Suite Manager State
  const [activeTestCaseQuestion, setActiveTestCaseQuestion] = useState<QuestionAdmin | null>(null);
  const [newTestCase, setNewTestCase] = useState<{
    input_data: string;
    expected_output: string;
    explanation: string;
    marks: number;
    display_order: number;
    is_hidden: boolean;
    category: TestCaseCategory;
  }>({
    input_data: "",
    expected_output: "",
    explanation: "",
    marks: 5,
    display_order: 1,
    is_hidden: true,
    category: "FUNCTIONAL",
  });
  const [tcSubmitting, setTcSubmitting] = useState(false);
  const [tcError, setTcError] = useState<string | null>(null);

  // Question Preview State
  const [previewQuestion, setPreviewQuestion] = useState<QuestionAdmin | null>(null);

  const [formData, setFormData] = useState<QuestionCreatePayload>({
    title: "",
    problem_description: "",
    input_format: "",
    output_format: "",
    constraints: "",
    difficulty: "MEDIUM",
    topic: "Arrays",
    marks: 20,
    time_limit_seconds: 2.0,
    memory_limit_mb: 256,
    display_order: 1,
    tags: "arrays,two-pointers",
    starter_code: "def solution():\n    pass\n",
    test_cases: [
      {
        input_data: "5\n1 2 3 4 5",
        expected_output: "15",
        explanation: "Sum of array elements is 15",
        marks: 5,
        display_order: 1,
        is_hidden: false,
        category: "SAMPLE",
      },
      {
        input_data: "3\n10 20 30",
        expected_output: "60",
        marks: 10,
        display_order: 2,
        is_hidden: true,
        category: "FUNCTIONAL",
      },
      {
        input_data: "1\n-5",
        expected_output: "-5",
        marks: 5,
        display_order: 3,
        is_hidden: true,
        category: "EDGE_CASE",
      },
    ],
  });

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    const res = await listQuestionsApi({
      difficulty: filterDifficulty || undefined,
      topic: filterTopic || undefined,
      search: searchQuery || undefined,
      is_archived: false,
    });
    if (res.success && res.data) {
      setQuestions(res.data);
    } else {
      setError(res.error?.message || "Failed to load questions.");
    }
    setLoading(false);
  }, [filterDifficulty, filterTopic, searchQuery]);

  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await loadQuestions();
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [loadQuestions]);

  const handleArchive = async (id: string) => {
    if (!confirm("Are you sure you want to archive this question?")) return;
    const res = await archiveQuestionApi(id);
    if (res.success) {
      await loadQuestions();
    } else {
      alert(res.error?.message || "Failed to archive question.");
    }
  };

  const handleValidateQuestion = async (qId: string) => {
    setValidatingQuestionId(qId);
    setValidationResult(null);
    const res = await validateQuestionApi(qId);
    if (res.success && res.data) {
      setValidationResult(res.data);
    } else {
      alert(res.error?.message || "Validation failed.");
    }
    setValidatingQuestionId(null);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    const res = await createQuestionApi(formData);
    if (res.success) {
      setShowCreateModal(false);
      await loadQuestions();
    } else {
      setFormError(res.error?.message || "Failed to create question.");
    }
    setFormSubmitting(false);
  };

  const handleAddTestCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTestCaseQuestion) return;
    setTcSubmitting(true);
    setTcError(null);

    const res = await addTestCaseApi(activeTestCaseQuestion.id, newTestCase);
    if (res.success && res.data) {
      const updatedQuestion = {
        ...activeTestCaseQuestion,
        test_cases: [...activeTestCaseQuestion.test_cases, res.data],
      };
      setActiveTestCaseQuestion(updatedQuestion);
      setQuestions((prev) =>
        prev.map((q) => (q.id === updatedQuestion.id ? updatedQuestion : q))
      );
      setNewTestCase({
        input_data: "",
        expected_output: "",
        explanation: "",
        marks: 5,
        display_order: activeTestCaseQuestion.test_cases.length + 2,
        is_hidden: true,
        category: "FUNCTIONAL",
      });
    } else {
      setTcError(res.error?.message || "Failed to add test case.");
    }
    setTcSubmitting(false);
  };

  const handleDeleteTestCase = async (questionId: string, testCaseId: string) => {
    if (!confirm("Delete this test case?")) return;
    const res = await deleteTestCaseApi(questionId, testCaseId);
    if (res.success) {
      if (activeTestCaseQuestion) {
        const updated = {
          ...activeTestCaseQuestion,
          test_cases: activeTestCaseQuestion.test_cases.filter((tc) => tc.id !== testCaseId),
        };
        setActiveTestCaseQuestion(updated);
        setQuestions((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
      }
    } else {
      alert(res.error?.message || "Failed to delete test case.");
    }
  };

  const handleUpdateTestCaseCategory = async (
    questionId: string,
    tc: TestCaseAdmin,
    newCategory: TestCaseCategory
  ) => {
    const isHidden = newCategory !== "SAMPLE";
    const res = await updateTestCaseApi(questionId, tc.id, {
      category: newCategory,
      is_hidden: isHidden,
    });
    if (res.success && res.data && activeTestCaseQuestion) {
      const updated = {
        ...activeTestCaseQuestion,
        test_cases: activeTestCaseQuestion.test_cases.map((item) =>
          item.id === tc.id ? res.data : item
        ),
      };
      setActiveTestCaseQuestion(updated);
      setQuestions((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
    }
  };

  return (
    <div className="bg-neutral-900 rounded-2xl border border-neutral-800 shadow-sm p-6 sm:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-800 pb-5">
        <div>
          <h2 className="text-xl font-bold text-neutral-100 tracking-tight flex items-center gap-2">
            <span>📚</span> Question Bank Repository
          </h2>
          <p className="text-sm text-neutral-400 mt-0.5">
            Manage coding challenges, configure test suites across Sample, Functional, and Edge cases, and validate coverage.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-white bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 rounded-xl shadow-sm transition"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
          </svg>
          Create Question
        </button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterDifficulty}
          onChange={(e) => setFilterDifficulty(e.target.value)}
          className="text-xs bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 font-semibold focus:outline-none focus:border-orange-500"
        >
          <option value="">All Difficulties</option>
          <option value="EASY">EASY</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HARD">HARD</option>
        </select>

        <div className="relative min-w-[220px]">
          <input
            type="text"
            placeholder="Search topic..."
            value={filterTopic}
            onChange={(e) => setFilterTopic(e.target.value)}
            className="w-full text-xs bg-neutral-950 border border-neutral-800 rounded-xl pl-8 pr-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
          />
          <svg className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <div className="relative min-w-[240px]">
          <input
            type="text"
            placeholder="Search title or tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs bg-neutral-950 border border-neutral-800 rounded-xl pl-8 pr-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
          />
          <svg className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
          </svg>
        </div>

        {(filterDifficulty || filterTopic || searchQuery) && (
          <button
            onClick={() => {
              setFilterDifficulty("");
              setFilterTopic("");
              setSearchQuery("");
            }}
            className="text-xs font-semibold text-orange-400 hover:underline"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Question List Table */}
      {loading ? (
        <div className="py-16 text-center text-sm text-neutral-400 space-y-3">
          <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p>Loading questions from repository...</p>
        </div>
      ) : error ? (
        <div className="py-4 text-center text-sm text-rose-400 bg-rose-950/40 border border-rose-900 rounded-xl">{error}</div>
      ) : questions.length === 0 ? (
        <div className="py-16 text-center text-sm text-neutral-500 max-w-md mx-auto space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-neutral-800 flex items-center justify-center mx-auto text-neutral-400">
            📖
          </div>
          <p className="font-semibold text-neutral-300">No Questions Found</p>
          <p className="text-xs text-neutral-500">Author a new question challenge to begin populating the repository.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-neutral-800">
          <table className="w-full text-left text-sm text-neutral-300">
            <thead className="bg-neutral-950/80 text-xs font-semibold text-neutral-400 uppercase tracking-wider border-b border-neutral-800">
              <tr>
                <th className="px-4 py-3">Question</th>
                <th className="px-4 py-3">Topic & Difficulty</th>
                <th className="px-4 py-3">Marks</th>
                <th className="px-4 py-3">Quality Indicators</th>
                <th className="px-4 py-3">Test Case Suite</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/80 text-xs">
              {questions.map((q) => {
                const sampleCount = q.test_cases.filter((tc) => tc.category === "SAMPLE" || !tc.is_hidden).length;
                const funcCount = q.test_cases.filter((tc) => tc.category === "FUNCTIONAL" && tc.is_hidden).length;
                const edgeCount = q.test_cases.filter((tc) => tc.category === "EDGE_CASE").length;

                return (
                  <tr key={q.id} className="hover:bg-neutral-800/30 transition">
                    <td className="px-4 py-3">
                      <div className="font-bold text-neutral-100 flex items-center gap-2">
                        <span>{q.title}</span>
                        {q.starter_code && (
                          <span className="text-[10px] bg-orange-950/80 text-orange-400 border border-orange-800/60 px-1.5 py-0.2 rounded font-mono">
                            Starter Code
                          </span>
                        )}
                      </div>
                      {q.tags && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {q.tags.split(",").map((t) => (
                            <span key={t} className="text-[10px] bg-neutral-800 text-neutral-400 px-1.5 py-0.5 rounded">
                              #{t.trim()}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className="bg-neutral-800 px-2 py-0.5 rounded text-[11px] text-neutral-300 font-medium">
                          {q.topic}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            q.difficulty === "EASY"
                              ? "bg-emerald-950/60 text-emerald-300 border border-emerald-800"
                              : q.difficulty === "HARD"
                              ? "bg-rose-950/60 text-rose-300 border border-rose-800"
                              : "bg-amber-950/60 text-amber-300 border border-amber-800"
                          }`}
                        >
                          {q.difficulty}
                        </span>
                      </div>
                    </td>

                    <td className="px-4 py-3 font-semibold text-neutral-200">
                      {q.marks} pts
                    </td>

                    <td className="px-4 py-3">
                      <div className="text-neutral-300 font-medium">
                        {q.solved_count ?? 0} / {q.total_attempts ?? 0} solved
                      </div>
                      <div className="text-[10px] text-orange-400">
                        Success Rate: {q.success_rate?.toFixed(1) ?? "0.0"}%
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        <span className="text-emerald-400 font-medium">{sampleCount} Sample</span>
                        <span>•</span>
                        <span className="text-neutral-300 font-medium">{funcCount} Functional</span>
                        <span>•</span>
                        <span className="text-cyan-400 font-medium">{edgeCount} Edge</span>
                      </div>
                    </td>

                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          onClick={() => handleValidateQuestion(q.id)}
                          disabled={validatingQuestionId === q.id}
                          className="px-2 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-[11px] font-medium transition"
                          title="Validate Test Cases & Mark Allocation"
                        >
                          {validatingQuestionId === q.id ? "Validating..." : "Validate"}
                        </button>
                        <button
                          onClick={() => setActiveTestCaseQuestion(q)}
                          className="px-2 py-1 bg-neutral-800 hover:bg-neutral-700 text-orange-400 border border-orange-500/20 rounded text-[11px] font-medium transition"
                          title="Manage Test Suite"
                        >
                          Test Suite
                        </button>
                        <button
                          onClick={() => setPreviewQuestion(q)}
                          className="px-2 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-[11px] font-medium transition"
                          title="Preview Question"
                        >
                          Preview
                        </button>
                        <button
                          onClick={() => handleArchive(q.id)}
                          className="text-rose-400 hover:text-rose-300 font-medium transition ml-1"
                        >
                          Archive
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pre-Flight Validation Modal */}
      {validationResult && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <h3 className="text-base font-bold text-neutral-100 flex items-center gap-2">
                <span>{validationResult.is_valid ? "✅" : "⚠️"}</span> Pre-Flight Question Validation
              </h3>
              <button
                onClick={() => setValidationResult(null)}
                className="text-neutral-400 hover:text-neutral-200 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-neutral-950 rounded-xl border border-neutral-800 grid grid-cols-2 gap-2">
                <div>Sample Tests: <b className="text-emerald-400">{validationResult.sample_test_count}</b></div>
                <div>Functional Tests: <b className="text-neutral-200">{validationResult.functional_test_count}</b></div>
                <div>Edge Cases: <b className="text-cyan-400">{validationResult.edge_test_count}</b></div>
                <div>Test Marks: <b className="text-orange-400">{validationResult.total_test_marks} / {validationResult.question_marks} pts</b></div>
              </div>

              {validationResult.errors.length > 0 && (
                <div className="p-3 bg-rose-950/40 border border-rose-900 text-rose-300 rounded-xl space-y-1">
                  <div className="font-bold uppercase tracking-wider text-[10px]">Blocking Errors ({validationResult.errors.length}):</div>
                  <ul className="list-disc list-inside space-y-0.5">
                    {validationResult.errors.map((e, idx) => (
                      <li key={idx}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {validationResult.warnings.length > 0 && (
                <div className="p-3 bg-amber-950/40 border border-amber-900 text-amber-300 rounded-xl space-y-1">
                  <div className="font-bold uppercase tracking-wider text-[10px]">Warnings ({validationResult.warnings.length}):</div>
                  <ul className="list-disc list-inside space-y-0.5">
                    {validationResult.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {validationResult.is_valid && validationResult.warnings.length === 0 && (
                <div className="p-3 bg-emerald-950/40 border border-emerald-900 text-emerald-300 rounded-xl">
                  Question passed all pre-flight validation checks! Adequate sample and private test cases configured with mark alignment.
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setValidationResult(null)}
                className="px-4 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded-xl text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Case Suite Manager Modal */}
      {activeTestCaseQuestion && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[88vh] overflow-y-auto p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <div>
                <span className="text-xs font-bold text-orange-400 uppercase">Test Case Suite Manager</span>
                <h3 className="text-lg font-bold text-neutral-100">{activeTestCaseQuestion.title}</h3>
              </div>
              <button
                onClick={() => setActiveTestCaseQuestion(null)}
                className="text-neutral-400 hover:text-neutral-200 text-lg"
              >
                ✕
              </button>
            </div>

            {/* Existing Test Cases List */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase text-neutral-400 tracking-wider">
                Configured Test Cases ({activeTestCaseQuestion.test_cases.length})
              </h4>
              {activeTestCaseQuestion.test_cases.length === 0 ? (
                <p className="text-xs text-neutral-500 italic py-4">No test cases configured yet.</p>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {activeTestCaseQuestion.test_cases.map((tc) => (
                    <div
                      key={tc.id}
                      className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl flex items-center justify-between text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-neutral-200">#{tc.display_order}</span>
                          <select
                            value={tc.category || (tc.is_hidden ? "FUNCTIONAL" : "SAMPLE")}
                            onChange={(e) =>
                              handleUpdateTestCaseCategory(
                                activeTestCaseQuestion.id,
                                tc,
                                e.target.value as TestCaseCategory
                              )
                            }
                            className="bg-neutral-900 border border-neutral-700 text-orange-400 text-[10px] rounded px-1.5 py-0.5 font-bold"
                          >
                            <option value="SAMPLE">SAMPLE (Public)</option>
                            <option value="FUNCTIONAL">FUNCTIONAL (Hidden)</option>
                            <option value="EDGE_CASE">EDGE_CASE (Hidden)</option>
                          </select>
                          <span className="text-neutral-400 font-semibold">{tc.marks} marks</span>
                        </div>
                        <div className="font-mono text-[11px] text-neutral-400">
                          In: {tc.input_data.slice(0, 30)}{tc.input_data.length > 30 ? "..." : ""} | Out: {tc.expected_output.slice(0, 30)}
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeleteTestCase(activeTestCaseQuestion.id, tc.id)}
                        className="text-rose-400 hover:text-rose-300 text-xs px-2 py-1 rounded bg-neutral-900 border border-neutral-800 transition"
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Add New Test Case Form */}
            <form onSubmit={handleAddTestCase} className="p-4 bg-neutral-950 border border-neutral-800 rounded-xl space-y-3">
              <h4 className="text-xs font-bold uppercase text-orange-400 tracking-wider">Add New Test Case</h4>
              {tcError && <p className="text-xs text-rose-400">{tcError}</p>}

              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="block text-neutral-400 mb-1">Category</label>
                  <select
                    value={newTestCase.category}
                    onChange={(e) => {
                      const cat = e.target.value as TestCaseCategory;
                      setNewTestCase((prev) => ({
                        ...prev,
                        category: cat,
                        is_hidden: cat !== "SAMPLE",
                      }));
                    }}
                    className="w-full bg-neutral-900 border border-neutral-700 text-neutral-200 rounded-lg p-2 text-xs"
                  >
                    <option value="SAMPLE">SAMPLE (Public)</option>
                    <option value="FUNCTIONAL">FUNCTIONAL (Hidden)</option>
                    <option value="EDGE_CASE">EDGE_CASE (Hidden)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-neutral-400 mb-1">Marks</label>
                  <input
                    type="number"
                    min="1"
                    value={newTestCase.marks}
                    onChange={(e) => setNewTestCase((prev) => ({ ...prev, marks: parseInt(e.target.value) || 0 }))}
                    className="w-full bg-neutral-900 border border-neutral-700 text-neutral-200 rounded-lg p-2 text-xs"
                  />
                </div>

                <div>
                  <label className="block text-neutral-400 mb-1">Display Order</label>
                  <input
                    type="number"
                    min="1"
                    value={newTestCase.display_order}
                    onChange={(e) => setNewTestCase((prev) => ({ ...prev, display_order: parseInt(e.target.value) || 1 }))}
                    className="w-full bg-neutral-900 border border-neutral-700 text-neutral-200 rounded-lg p-2 text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-neutral-400 mb-1">Standard Input</label>
                  <textarea
                    rows={2}
                    value={newTestCase.input_data}
                    onChange={(e) => setNewTestCase((prev) => ({ ...prev, input_data: e.target.value }))}
                    placeholder="Input provided to student solution..."
                    className="w-full bg-neutral-900 border border-neutral-700 text-neutral-200 rounded-lg p-2 font-mono text-xs"
                    required
                  />
                </div>

                <div>
                  <label className="block text-neutral-400 mb-1">Expected Output</label>
                  <textarea
                    rows={2}
                    value={newTestCase.expected_output}
                    onChange={(e) => setNewTestCase((prev) => ({ ...prev, expected_output: e.target.value }))}
                    placeholder="Expected standard output..."
                    className="w-full bg-neutral-900 border border-neutral-700 text-neutral-200 rounded-lg p-2 font-mono text-xs"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-neutral-400 mb-1 text-xs">Explanation (Optional for sample cases)</label>
                <input
                  type="text"
                  value={newTestCase.explanation}
                  onChange={(e) => setNewTestCase((prev) => ({ ...prev, explanation: e.target.value }))}
                  placeholder="Explain the sample transformation..."
                  className="w-full bg-neutral-900 border border-neutral-700 text-neutral-200 rounded-lg p-2 text-xs"
                />
              </div>

              <div className="flex justify-end pt-1">
                <button
                  type="submit"
                  disabled={tcSubmitting}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-semibold transition disabled:opacity-50"
                >
                  {tcSubmitting ? "Adding..." : "Add Test Case to Suite"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Question Preview Modal */}
      {previewQuestion && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <div>
                <span className="text-xs font-bold text-orange-400 uppercase">Question Preview</span>
                <h3 className="text-lg font-bold text-neutral-100">{previewQuestion.title}</h3>
              </div>
              <button
                onClick={() => setPreviewQuestion(null)}
                className="text-neutral-400 hover:text-neutral-200 text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs text-neutral-300">
              <div className="flex items-center gap-2">
                <span className="bg-neutral-800 px-2.5 py-0.5 rounded font-medium">{previewQuestion.topic}</span>
                <span className="bg-neutral-800 px-2.5 py-0.5 rounded font-bold text-orange-400">{previewQuestion.difficulty}</span>
                <span className="text-neutral-400">{previewQuestion.marks} marks • {previewQuestion.time_limit_seconds}s limit</span>
              </div>

              <div>
                <h4 className="font-bold text-neutral-200 mb-1">Description:</h4>
                <p className="whitespace-pre-wrap leading-relaxed text-neutral-300">{previewQuestion.problem_description}</p>
              </div>

              {previewQuestion.input_format && (
                <div>
                  <h4 className="font-bold text-neutral-200 mb-1">Input Format:</h4>
                  <p className="text-neutral-400">{previewQuestion.input_format}</p>
                </div>
              )}

              {previewQuestion.output_format && (
                <div>
                  <h4 className="font-bold text-neutral-200 mb-1">Output Format:</h4>
                  <p className="text-neutral-400">{previewQuestion.output_format}</p>
                </div>
              )}

              {previewQuestion.constraints && (
                <div>
                  <h4 className="font-bold text-neutral-200 mb-1">Constraints:</h4>
                  <p className="text-neutral-400 font-mono text-[11px]">{previewQuestion.constraints}</p>
                </div>
              )}

              {previewQuestion.starter_code && (
                <div>
                  <h4 className="font-bold text-neutral-200 mb-1">Starter Code Template:</h4>
                  <pre className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl font-mono text-[11px] text-orange-300 overflow-x-auto">
                    {previewQuestion.starter_code}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setPreviewQuestion(null)}
                className="px-4 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded-xl text-xs font-semibold transition"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-neutral-900 rounded-3xl border border-neutral-800 shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-7 space-y-5">
            <div className="flex justify-between items-center border-b border-neutral-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-neutral-100 tracking-tight">Author New Question</h3>
                <p className="text-xs text-neutral-400">Specify problem statements, starter templates, tags, and initial test suite.</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-neutral-400 hover:text-neutral-200 text-lg"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 text-xs bg-rose-950/40 border border-rose-900 text-rose-300 rounded-xl">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-neutral-200 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Reverse Words in a String"
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-neutral-200 mb-1">Topic</label>
                  <input
                    type="text"
                    required
                    value={formData.topic}
                    onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-neutral-200 mb-1">Difficulty</label>
                  <select
                    value={formData.difficulty}
                    onChange={(e) => setFormData({ ...formData, difficulty: e.target.value as DifficultyLevel })}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                  >
                    <option value="EASY">EASY</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HARD">HARD</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-semibold text-neutral-200 mb-1">Total Marks</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.marks}
                    onChange={(e) => setFormData({ ...formData, marks: parseInt(e.target.value) || 1 })}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-neutral-200 mb-1">Time Limit (s)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="15"
                    value={formData.time_limit_seconds}
                    onChange={(e) => setFormData({ ...formData, time_limit_seconds: parseFloat(e.target.value) || 1.0 })}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-neutral-200 mb-1">Memory Limit (MB)</label>
                  <input
                    type="number"
                    min="16"
                    max="1024"
                    value={formData.memory_limit_mb}
                    onChange={(e) => setFormData({ ...formData, memory_limit_mb: parseInt(e.target.value) || 256 })}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-neutral-200 mb-1">Tags (Comma-separated)</label>
                <input
                  type="text"
                  value={formData.tags || ""}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="e.g. strings, two-pointers, hash-map"
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-neutral-200 mb-1">Starter Code Template</label>
                <textarea
                  rows={2}
                  value={formData.starter_code || ""}
                  onChange={(e) => setFormData({ ...formData, starter_code: e.target.value })}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 font-mono text-xs focus:outline-none focus:border-orange-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-neutral-200 mb-1">Problem Description</label>
                <textarea
                  required
                  rows={3}
                  value={formData.problem_description}
                  onChange={(e) => setFormData({ ...formData, problem_description: e.target.value })}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-neutral-200 focus:outline-none focus:border-orange-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-neutral-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-neutral-800 text-neutral-300 rounded-xl text-xs font-semibold hover:bg-neutral-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-5 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-semibold transition disabled:opacity-50"
                >
                  {formSubmitting ? "Creating..." : "Save Question"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
