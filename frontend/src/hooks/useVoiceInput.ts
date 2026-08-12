import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionAlternativeLike = { transcript: string; confidence: number };
type SpeechRecognitionResultLike = { isFinal: boolean; length: number; [index: number]: SpeechRecognitionAlternativeLike };
type SpeechRecognitionEventLike = { resultIndex: number; results: { length: number; [index: number]: SpeechRecognitionResultLike } };
type SpeechRecognitionErrorEventLike = { error: string };

type RecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
};

type RecognitionConstructor = new () => RecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  }
}

export type VoiceTranscriber = "browser" | "groq";

const configuredProvider: VoiceTranscriber = import.meta.env.VITE_VOICE_TRANSCRIBER === "groq" ? "groq" : "browser";
const punctuationEnabled = import.meta.env.VITE_VOICE_PUNCTUATION === "true";
const silenceDelayMs = 1800;
const noSpeechDelayMs = 6500;
const lowConfidence = 0.55;

const punctuationCommands: Array<[RegExp, string]> = [
  [/\bquestion mark\b/gi, "?"],
  [/\bexclamation mark\b/gi, "!"],
  [/\bfull stop\b/gi, "."],
  [/\bperiod\b/gi, "."],
  [/\bcomma\b/gi, ","],
  [/\bsemicolon\b/gi, ";"],
  [/\bcolon\b/gi, ":"],
  [/\bnew line\b/gi, "\n"],
];

function formatVoiceText(text: string) {
  if (!punctuationEnabled) return text.trim();
  return punctuationCommands.reduce((formatted, [pattern, replacement]) => formatted.replace(pattern, replacement), text)
    .replace(/\s+([,.:;!?])/g, "$1")
    .replace(/\n\s+/g, "\n")
    .trim();
}

function getRecognitionConstructor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition;
}

function joinedText(prefix: string, finalText: string, interimText = "") {
  return [prefix, finalText, interimText].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
}

/**
 * Swappable transcription adapter. "groq" deliberately calls the isolated
 * application proxy so an API key is never bundled into the browser.
 */
export async function transcribeAudio(audio: Blob, provider: VoiceTranscriber = configuredProvider): Promise<string> {
  if (provider !== "groq") return "";
  const form = new FormData();
  form.append("audio", audio, "mitra-dictation.webm");
  const response = await fetch("/api/voice/transcribe", { method: "POST", body: form });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Voice transcription was unavailable.");
  return typeof body.text === "string" ? body.text.trim() : "";
}

export function useVoiceInput({
  value,
  onInterim,
  onFinal,
}: {
  value: string;
  onInterim: (text: string) => void;
  onFinal: (text: string) => void;
}) {
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [hint, setHint] = useState("");
  const recognitionRef = useRef<RecognitionLike | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const silenceTimerRef = useRef<number | null>(null);
  const noSpeechTimerRef = useRef<number | null>(null);
  const prefixRef = useRef("");
  const finalRef = useRef("");
  const interimRef = useRef("");
  const chunksRef = useRef<Blob[]>([]);
  const heardSpeechRef = useRef(false);
  const lowConfidenceRef = useRef(false);
  const endingRef = useRef(false);
  const completedRef = useRef(false);
  const listeningRef = useRef(false);
  const latestValueRef = useRef(value);
  const onInterimRef = useRef(onInterim);
  const onFinalRef = useRef(onFinal);

  useEffect(() => { latestValueRef.current = value; }, [value]);
  useEffect(() => { onInterimRef.current = onInterim; }, [onInterim]);
  useEffect(() => { onFinalRef.current = onFinal; }, [onFinal]);

  const hasNativeRecognition = typeof window !== "undefined" && Boolean(getRecognitionConstructor());
  const isSupported = hasNativeRecognition || (configuredProvider === "groq" && typeof MediaRecorder !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia));

  const clearTimers = useCallback(() => {
    if (silenceTimerRef.current !== null) window.clearTimeout(silenceTimerRef.current);
    if (noSpeechTimerRef.current !== null) window.clearTimeout(noSpeechTimerRef.current);
    silenceTimerRef.current = null;
    noSpeechTimerRef.current = null;
  }, []);

  const stopMeter = useCallback(() => {
    if (animationFrameRef.current !== null) cancelAnimationFrame(animationFrameRef.current);
    animationFrameRef.current = null;
    setAudioLevel(0);
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
  }, []);

  const complete = useCallback((text: string) => {
    if (completedRef.current) return;
    completedRef.current = true;
    const transcript = formatVoiceText(text);
    if (!transcript) {
      setHint("Didn't catch that, try again.");
      return;
    }
    if (lowConfidenceRef.current && configuredProvider === "browser") setHint("Low confidence — please review before sending.");
    else setHint("");
    onFinalRef.current(transcript);
  }, []);

  const stopListening = useCallback((reason: "manual" | "silence" | "timeout" = "manual") => {
    if (!listeningRef.current || endingRef.current) return;
    endingRef.current = true;
    listeningRef.current = false;
    clearTimers();
    setIsListening(false);
    recognitionRef.current?.stop();
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      setIsTranscribing(true);
      recorder.stop();
    } else {
      stopMeter();
      const text = joinedText(prefixRef.current, finalRef.current, interimRef.current);
      if (reason === "timeout" && !heardSpeechRef.current) setHint("Didn't catch that, try again.");
      complete(text);
    }
  }, [clearTimers, complete, stopMeter]);

  const startMeter = useCallback((stream: MediaStream) => {
    const AudioContextConstructor = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextConstructor) return;
    const context = new AudioContextConstructor();
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    context.createMediaStreamSource(stream).connect(analyser);
    const samples = new Uint8Array(analyser.fftSize);
    const measure = () => {
      analyser.getByteTimeDomainData(samples);
      const level = samples.reduce((sum, sample) => sum + Math.abs(sample - 128), 0) / samples.length / 32;
      const normalizedLevel = Math.min(1, level);
      setAudioLevel(normalizedLevel);
      if (normalizedLevel > 0.045) {
        heardSpeechRef.current = true;
        if (silenceTimerRef.current !== null) window.clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = window.setTimeout(() => stopListening("silence"), silenceDelayMs);
      }
      animationFrameRef.current = requestAnimationFrame(measure);
    };
    audioContextRef.current = context;
    measure();
  }, [stopListening]);

  const startListening = useCallback(async () => {
    if (!isSupported || isListening || isTranscribing) return;
    setHint("");
    setIsListening(true);
    listeningRef.current = true;
    endingRef.current = false;
    completedRef.current = false;
    heardSpeechRef.current = false;
    lowConfidenceRef.current = false;
    prefixRef.current = latestValueRef.current.trim();
    finalRef.current = "";
    interimRef.current = "";
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      streamRef.current = stream;
      startMeter(stream);
      noSpeechTimerRef.current = window.setTimeout(() => stopListening("timeout"), noSpeechDelayMs);

      if (configuredProvider === "groq") {
        const preferredMime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find(type => MediaRecorder.isTypeSupported(type));
        const recorder = preferredMime ? new MediaRecorder(stream, { mimeType: preferredMime }) : new MediaRecorder(stream);
        recorderRef.current = recorder;
        recorder.ondataavailable = event => { if (event.data.size) chunksRef.current.push(event.data); };
        recorder.onstop = async () => {
          recorderRef.current = null;
          stopMeter();
          try {
            const transcript = await transcribeAudio(new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" }), "groq");
            complete(joinedText(prefixRef.current, transcript));
          } catch (error) {
            setHint(error instanceof Error ? error.message : "Voice transcription was unavailable.");
          } finally {
            setIsTranscribing(false);
          }
        };
        recorder.start(250);
      }

      const Recognition = getRecognitionConstructor();
      if (Recognition) {
        const recognition = new Recognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = navigator.language || "en-US";
        recognition.maxAlternatives = 3;
        recognition.onresult = event => {
          let nextFinal = "";
          let nextInterim = "";
          for (let index = event.resultIndex; index < event.results.length; index += 1) {
            const result = event.results[index];
            const alternative = result[0];
            if (!alternative) continue;
            heardSpeechRef.current = true;
            if (result.isFinal) {
              nextFinal += `${alternative.transcript} `;
              if (alternative.confidence > 0 && alternative.confidence < lowConfidence) lowConfidenceRef.current = true;
            } else nextInterim += `${alternative.transcript} `;
          }
          if (nextFinal) finalRef.current = `${finalRef.current} ${nextFinal}`.trim();
          interimRef.current = nextInterim.trim();
          onInterimRef.current(joinedText(prefixRef.current, finalRef.current, interimRef.current));
        };
        recognition.onerror = event => {
          if (event.error === "no-speech") return;
          if (["not-allowed", "service-not-allowed", "audio-capture"].includes(event.error)) {
            setHint("Microphone permission was denied. Allow it in your browser settings and try again.");
          } else setHint("Voice input had a problem. Please try again.");
        };
        recognition.onend = () => {
          recognitionRef.current = null;
          if (configuredProvider === "browser" && endingRef.current) complete(joinedText(prefixRef.current, finalRef.current, interimRef.current));
        };
        recognitionRef.current = recognition;
        recognition.start();
      }
    } catch (error) {
      stopMeter();
      setIsListening(false);
      listeningRef.current = false;
      setHint(error instanceof DOMException && error.name === "NotAllowedError" ? "Microphone permission was denied. Allow it in your browser settings and try again." : "Could not start voice input. Please try again.");
    }
  }, [complete, isListening, isSupported, isTranscribing, startMeter, stopListening, stopMeter]);

  const toggleListening = useCallback(() => {
    if (isListening) stopListening();
    else void startListening();
  }, [isListening, startListening, stopListening]);

  useEffect(() => () => {
    clearTimers();
    recognitionRef.current?.abort();
    listeningRef.current = false;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    stopMeter();
  }, [clearTimers, stopMeter]);

  return { isListening, isTranscribing, audioLevel, hint, isSupported, toggleListening };
}
