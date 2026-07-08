"use client";

import { useEffect } from "react";

/**
 * Last-resort error boundary. `app/error.tsx` cannot catch errors thrown by the
 * root layout itself (the providers, the auth gate). `global-error.tsx`
 * replaces the entire document in that case, so even a failure above the
 * providers shows a usable message and a reload button instead of a blank page.
 * It must be fully self-contained — it cannot rely on the i18n provider (which
 * may be the thing that failed), so the copy here is intentionally hardcoded.
 */
export default function GlobalError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global render error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          fontFamily: "system-ui, sans-serif",
          background: "#f7f4ee",
          color: "#1a1a1a",
          padding: "1.5rem"
        }}
      >
        <div
          style={{
            maxWidth: "32rem",
            textAlign: "center",
            border: "1px solid #d9d2c5",
            background: "#fff",
            padding: "2rem",
            borderRadius: "2px"
          }}
        >
          <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: 0 }}>
            Something went wrong
          </h1>
          <p style={{ marginTop: "0.75rem", fontSize: "0.875rem", lineHeight: 1.6, color: "#555" }}>
            UniWay hit an unexpected error while loading this page. This is usually temporary.
            Please reload and try again.
          </p>
          <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem", justifyContent: "center" }}>
            <button
              onClick={() => reset()}
              style={{
                minHeight: "2.75rem",
                padding: "0 1rem",
                border: "none",
                background: "#9e1b32",
                color: "#fff",
                fontWeight: 600,
                borderRadius: "2px",
                cursor: "pointer"
              }}
              type="button"
            >
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                minHeight: "2.75rem",
                padding: "0 1rem",
                border: "1px solid #d9d2c5",
                background: "#fff",
                color: "#1a1a1a",
                fontWeight: 600,
                borderRadius: "2px",
                cursor: "pointer"
              }}
              type="button"
            >
              Reload
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
