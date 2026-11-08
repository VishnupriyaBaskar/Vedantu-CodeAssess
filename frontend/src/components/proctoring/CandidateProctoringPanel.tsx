"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  endProctoringSessionApi,
  sendProctoringEventsApi,
  sendProctoringHeartbeatApi,
  startProctoringSessionApi,
  submitProctoringConsentApi,
} from "@/lib/api/proctoring";
import { ProctoringConfig, ProctoringSessionStartResponse } from "@/types/proctoring";

interface CandidateProctoringPanelProps {
  assessmentId: string;
  attemptId: string;
  onConsentComplete?: () => void;
  isExamCompleted?: boolean;
}

export function CandidateProctoringPanel({
  assessmentId,
  attemptId,
  onConsentComplete,
  isExamCompleted = false,
}: CandidateProctoringPanelProps) {
  const [session, setSession] = useState<ProctoringSessionStartResponse | null>(null);
  const [consentGiven, setConsentGiven] = useState(false);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [showCameraPip, setShowCameraPip] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [eventCount, setEventCount] = useState(0);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const blurStartRef = useRef<number | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    toastTimeoutRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  }, []);

  const sendEvent = useCallback(
    async (eventType: string, severity: "LOW" | "MEDIUM" | "HIGH" = "LOW", metadata: Record<string, unknown> = {}) => {
      if (!session || !consentGiven || isExamCompleted) return;
      try {
        await sendProctoringEventsApi(session.session_id, [
          {
            event_type: eventType,
            severity,
            event_metadata: metadata,
            recorded_at: new Date().toISOString(),
          },
        ]);
        setEventCount((prev) => prev + 1);
      } catch (err) {
        console.error("Failed to transmit proctoring event:", err);
      }
    },
    [session, consentGiven, isExamCompleted]
  );

  // Initialize proctoring session on mount
  useEffect(() => {
    let ignore = false;
    async function initSession() {
      try {
        const res = await startProctoringSessionApi(assessmentId, attemptId);
        if (res.success && res.data && !ignore) {
          setSession(res.data);
          if (res.data.consent_given) {
            setConsentGiven(true);
            if (onConsentComplete) onConsentComplete();
          } else {
            setShowConsentModal(true);
          }
        }
      } catch (err) {
        console.error("Proctoring session initialization error:", err);
      }
    }

    if (assessmentId && attemptId && !isExamCompleted) {
      initSession();
    }

    return () => {
      ignore = true;
    };
  }, [assessmentId, attemptId, isExamCompleted, onConsentComplete]);

  // Handle webcam initialization when required and consent is granted
  useEffect(() => {
    if (!consentGiven || !session?.monitoring_config.enable_webcam || isExamCompleted) return;

    let localStream: MediaStream | null = null;
    async function setupCamera() {
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 320 }, height: { ideal: 240 } },
          audio: false,
        });
        mediaStreamRef.current = localStream;
        if (videoRef.current) {
          videoRef.current.srcObject = localStream;
        }
        setCameraActive(true);
        setCameraError(null);
      } catch (err: unknown) {
        console.warn("Camera access denied or unavailable:", err);
        const errName = (err as Error)?.name || "UnknownError";
        const isDenied = errName === "NotAllowedError" || errName === "PermissionDeniedError";
        setCameraError(isDenied ? "Camera permission denied" : "Camera unavailable");
        setCameraActive(false);

        sendEvent(
          isDenied ? "CAMERA_PERMISSION_DENIED" : "CAMERA_UNAVAILABLE",
          "LOW",
          { error_name: errName }
        );
      }
    }

    setupCamera();

    return () => {
      if (localStream) {
        localStream.getTracks().forEach((track) => track.stop());
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
    };
  }, [consentGiven, session?.monitoring_config.enable_webcam, isExamCompleted, sendEvent]);

  // Heartbeat ping interval
  useEffect(() => {
    if (!consentGiven || !session || isExamCompleted) return;

    heartbeatTimerRef.current = setInterval(async () => {
      try {
        await sendProctoringHeartbeatApi(session.session_id);
      } catch {
        // Silent heartbeat error
      }
    }, 20000);

    return () => {
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    };
  }, [consentGiven, session, isExamCompleted]);

  // Fullscreen, blur, and visibility event listeners
  useEffect(() => {
    if (!consentGiven || !session || isExamCompleted) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        sendEvent("TAB_SWITCH", "MEDIUM", { trigger: "document_hidden" });
        showToast("Integrity Notice: Please remain on your assessment window.");
      } else {
        sendEvent("PAGE_VISIBLE", "LOW");
      }
    };

    const handleWindowBlur = () => {
      blurStartRef.current = Date.now();
      sendEvent("WINDOW_BLUR", "LOW");
    };

    const handleWindowFocus = () => {
      let durationSec = 0;
      if (blurStartRef.current) {
        durationSec = Math.round((Date.now() - blurStartRef.current) / 1000);
        blurStartRef.current = null;
      }
      sendEvent("WINDOW_FOCUS", "LOW", { blur_duration_seconds: durationSec });
    };

    const handleFullscreenChange = () => {
      const isFs = !!document.fullscreenElement;
      setIsFullscreen(isFs);
      if (isFs) {
        sendEvent("FULLSCREEN_ENTER", "LOW");
      } else {
        sendEvent("FULLSCREEN_EXIT", "MEDIUM");
        showToast("Integrity Notice: Fullscreen mode was exited. Please re-enter fullscreen.");
      }
    };

    const handleBeforeUnload = () => {
      // Best-effort beacon
      sendEvent("PAGE_RELOADED", "MEDIUM", { trigger: "beforeunload" });
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleWindowBlur);
    window.addEventListener("focus", handleWindowFocus);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleWindowBlur);
      window.removeEventListener("focus", handleWindowFocus);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [consentGiven, session, isExamCompleted, sendEvent, showToast]);

  // Stop camera tracks and end proctoring on completion
  useEffect(() => {
    if (isExamCompleted && session) {
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
      endProctoringSessionApi(session.session_id).catch(() => {});
    }
  }, [isExamCompleted, session]);

  const requestFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
        setIsFullscreen(true);
      }
    } catch (err) {
      console.warn("Fullscreen request failed:", err);
    }
  };

  const handleGrantConsent = async () => {
    if (!session) return;
    try {
      const res = await submitProctoringConsentApi(session.session_id, true);
      if (res.success) {
        setConsentGiven(true);
        setShowConsentModal(false);
        if (session.monitoring_config.require_fullscreen) {
          await requestFullscreen();
        }
        if (onConsentComplete) onConsentComplete();
      }
    } catch (err) {
      console.error("Failed to submit proctoring consent:", err);
    }
  };

  const config: ProctoringConfig = session?.monitoring_config || {
    enable_webcam: false,
    require_fullscreen: true,
    enable_tab_monitoring: true,
    enable_focus_monitoring: true,
    max_tab_switches_warning: 2,
    max_tab_switches_alert: 4,
    max_blur_seconds_alert: 60,
    max_fullscreen_exits_alert: 3,
  };

  return (
    <>
      {/* ------------------------------------------------------------------ */}
      {/* Pre-Exam Consent Modal */}
      {/* ------------------------------------------------------------------ */}
      {showConsentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl max-w-xl w-full p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-orange-50 dark:bg-orange-950/60 border border-orange-200 dark:border-orange-800 flex items-center justify-center text-orange-600 dark:text-orange-400">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  Assessment Integrity & Privacy Notice
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Please review the examination safeguards before commencing your session.
                </p>
              </div>
            </div>

            <div className="space-y-3.5 text-xs text-slate-600 dark:text-slate-300">
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 space-y-2">
                <p className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  Active Integrity Monitoring Protocols:
                </p>
                <ul className="list-disc pl-5 space-y-1 text-slate-500 dark:text-slate-400">
                  {config.require_fullscreen && (
                    <li>Fullscreen mode is required to maintain test isolation.</li>
                  )}
                  {config.enable_tab_monitoring && (
                    <li>Browser tab switches and minimizing the exam window will be logged.</li>
                  )}
                  {config.enable_focus_monitoring && (
                    <li>Losing window focus or interacting with external applications is audited.</li>
                  )}
                  {config.enable_webcam && (
                    <li>A local webcam presence indicator is enabled for this assessment.</li>
                  )}
                </ul>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/50 dark:border-emerald-800/40 text-emerald-800 dark:text-emerald-300 space-y-1">
                <p className="font-semibold flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Privacy-First Guarantee:
                </p>
                <p className="text-[11px] leading-relaxed opacity-90">
                  No facial recognition, biometric profiling, or emotion inference is performed. 
                  Webcam streams are rendered strictly locally for verification and are not recorded or stored by default. 
                  All integrity events are signals for manual instructor review and never cause automated disqualification.
                </p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={handleGrantConsent}
                className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-semibold text-xs tracking-wide shadow-md hover:shadow-orange-500/20 transition-all flex items-center justify-center gap-2"
              >
                <span>Accept Terms & Begin Examination</span>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Toast Notification Banner */}
      {/* ------------------------------------------------------------------ */}
      {toastMessage && (
        <div className="fixed top-5 left-1/2 -translate-x-1/2 z-50 animate-bounce-subtle">
          <div className="px-4 py-2.5 rounded-2xl bg-amber-500/95 text-slate-950 font-bold text-xs shadow-lg flex items-center gap-2.5 border border-amber-300">
            <svg className="w-4 h-4 text-slate-950 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Active Proctoring Status Pill Bar */}
      {/* ------------------------------------------------------------------ */}
      {consentGiven && !isExamCompleted && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Integrity Status Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-900/60 border border-slate-700/60 text-slate-300 backdrop-blur-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-semibold text-[11px] tracking-wide uppercase text-emerald-400">
              Integrity Active
            </span>
          </div>

          {/* Fullscreen Status */}
          {config.require_fullscreen && (
            <button
              type="button"
              onClick={requestFullscreen}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl border text-[11px] font-medium transition-all ${
                isFullscreen
                  ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300"
                  : "bg-amber-950/60 border-amber-700 text-amber-300 hover:bg-amber-900/60 animate-pulse"
              }`}
              title={isFullscreen ? "Fullscreen active" : "Click to enter required fullscreen mode"}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {isFullscreen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                )}
              </svg>
              <span>{isFullscreen ? "Fullscreen Mode" : "Enter Fullscreen"}</span>
            </button>
          )}

          {/* Camera Status */}
          {config.enable_webcam && (
            <div
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl border text-[11px] font-medium ${
                cameraActive
                  ? "bg-slate-900/60 border-emerald-800/60 text-emerald-300"
                  : "bg-rose-950/60 border-rose-800/60 text-rose-300"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${cameraActive ? "bg-emerald-400" : "bg-rose-400"}`}></span>
              <span>{cameraActive ? "Camera Monitored" : cameraError || "Camera Off"}</span>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Live Self-Preview PIP Window (Local Feed Only) */}
      {/* ------------------------------------------------------------------ */}
      {consentGiven && config.enable_webcam && !isExamCompleted && cameraActive && (
        <div
          className={`fixed bottom-4 right-4 z-40 rounded-2xl overflow-hidden border border-slate-700/70 bg-slate-900 shadow-2xl transition-all duration-300 ${
            showCameraPip ? "w-44 h-32 sm:w-52 sm:h-36" : "w-10 h-10 rounded-full"
          }`}
        >
          {showCameraPip ? (
            <div className="relative w-full h-full group">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover transform -scale-x-100"
              />
              <div className="absolute top-1.5 left-2 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-950/70 backdrop-blur-sm text-[10px] text-emerald-400 border border-slate-700/50">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Live Feed</span>
              </div>
              <button
                type="button"
                onClick={() => setShowCameraPip(false)}
                className="absolute top-1.5 right-1.5 p-1 rounded-full bg-slate-950/70 hover:bg-slate-800 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Minimize preview"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div className="absolute bottom-1 left-2 text-[9px] text-slate-400 tracking-wider">
                Privacy-Protected (Not Saved)
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowCameraPip(true)}
              className="w-full h-full flex items-center justify-center bg-slate-800 hover:bg-slate-700 text-emerald-400"
              title="Expand camera preview"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          )}
        </div>
      )}
    </>
  );
}
