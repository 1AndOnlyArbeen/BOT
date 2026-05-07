import { useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import clsx from "clsx";

export function VoiceRecorder({ onAudio, disabled }: { onAudio: (b: Blob) => void; disabled?: boolean }) {
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        onAudio(blob);
      };
      mr.start();
      recorderRef.current = mr;
      setRecording(true);
    } catch (e) {
      alert("Microphone permission denied or unavailable");
    }
  };

  const stop = () => {
    recorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <button
      onClick={recording ? stop : start}
      disabled={disabled}
      className={clsx(
        "p-3 rounded-xl border transition-all",
        recording
          ? "bg-accent text-white border-accent glow animate-pulse-glow"
          : "bg-panel2 border-border text-muted hover:text-text hover:border-muted",
        disabled && "opacity-50 cursor-not-allowed",
      )}
      title={recording ? "Stop recording" : "Record voice"}
    >
      {recording ? <Square className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
    </button>
  );
}
