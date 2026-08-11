import mermaid from "mermaid";
import { useEffect, useRef, useState } from "react";
import { Copy, Check } from "lucide-react";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    primaryColor: "#00d4ff",
    primaryTextColor: "#eaf0ff",
    primaryBorderColor: "#8c77ff",
    lineColor: "#42d7b9",
    secondaryColor: "#141c37",
    tertiaryColor: "#0a0e1a"
  }
});

export function MermaidRenderer({ diagram }: { diagram: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (ref.current && diagram) {
      ref.current.innerHTML = "";
      mermaid.render(`mermaid-${crypto.randomUUID()}`, diagram)
        .then(({ svg }) => {
          if (ref.current) ref.current.innerHTML = svg;
        })
        .catch((e) => console.error("Mermaid error:", e));
    }
  }, [diagram]);

  const copyCode = () => {
    navigator.clipboard.writeText(diagram);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mermaid-container">
      <button onClick={copyCode} title="Copy Mermaid Code">
        {copied ? <Check size={16} color="var(--accent-green)" /> : <Copy size={16} />}
      </button>
      <div ref={ref} />
    </div>
  );
}
