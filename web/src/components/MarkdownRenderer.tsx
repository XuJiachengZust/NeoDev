import { useEffect, useRef, useId, type ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import mermaid from "mermaid";

// 初始化 mermaid 配置（暗色主题）
mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    darkMode: true,
    background: "#1a1a24",
    primaryColor: "#B026FF",
    primaryTextColor: "#e0e0e0",
    lineColor: "#00F0FF",
    secondaryColor: "#2a2a33",
    tertiaryColor: "#1e1e2a",
  },
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 12,
});

/** Mermaid 图表渲染块 */
function MermaidBlock({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const uniqueId = useId().replace(/:/g, "_");

  useEffect(() => {
    if (!containerRef.current || !chart.trim()) return;
    let cancelled = false;

    (async () => {
      try {
        const { svg } = await mermaid.render(`mermaid${uniqueId}`, chart.trim());
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch {
        if (!cancelled && containerRef.current) {
          containerRef.current.textContent = chart;
          containerRef.current.classList.add("mermaid-error");
        }
      }
    })();

    return () => { cancelled = true; };
  }, [chart, uniqueId]);

  return <div ref={containerRef} className="md-mermaid" />;
}

/** 自定义 code 块：mermaid 语言走图表渲染，其余走 highlight.js */
function CodeBlock({ className, children, ...props }: ComponentPropsWithoutRef<"code"> & { node?: unknown }) {
  const { node: _node, ...rest } = props;
  const match = /language-(\w+)/.exec(className || "");
  const lang = match?.[1];
  const code = String(children).replace(/\n$/, "");

  // 行内 code
  if (!className && !code.includes("\n")) {
    return <code className="md-inline-code" {...rest}>{children}</code>;
  }

  if (lang === "mermaid") {
    return <MermaidBlock chart={code} />;
  }

  return (
    <code className={className} {...rest}>
      {children}
    </code>
  );
}

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={`md-renderer ${className ?? ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code: CodeBlock,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
