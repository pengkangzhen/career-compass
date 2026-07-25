import { useCallback, useRef, useState } from "react";

// Lightweight toast — single active message, auto-dismissed after duration.
// No portal / no queue: this is enough for command-feedback UX.
export function useToast(defaultDurationMs = 4000) {
  const [toast, setToast] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  const show = useCallback(
    (msg: string, durationMs = defaultDurationMs) => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
      setToast(msg);
      timerRef.current = window.setTimeout(() => {
        setToast(null);
        timerRef.current = null;
      }, durationMs);
    },
    [defaultDurationMs],
  );

  const dismiss = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setToast(null);
  }, []);

  return { toast, show, dismiss };
}
