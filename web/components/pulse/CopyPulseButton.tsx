"use client";

import { useState } from "react";

export function CopyPulseButton({ markdown }: { markdown: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-lg border border-hairline bg-surface px-3 py-2 text-xs font-semibold text-ink hover:bg-canvas"
    >
      {copied ? "Copied" : "Copy pulse"}
    </button>
  );
}
