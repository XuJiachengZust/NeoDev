import { useEffect, useRef, useId, useState, useCallback, type ComponentPropsWithoutRef, type WheelEvent as ReactWheelEvent, type MouseEvent as ReactMouseEvent } from "react";
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

/** Mermaid 全屏查看弹层 */
function MermaidZoomOverlay({ svgHtml, onClose }: { svgHtml: string; onClose: () => void }) {
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  const handleWheel = useCallback((e: ReactWheelEvent) => {
    e.stopPropagation();
    setScale((s) => {
      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      return Math.min(Math.max(s * factor, 0.1), 50);
    });
  }, []);

  const handleMouseDown = useCallback((e: ReactMouseEvent) => {
    if (e.button !== 0) return;
    dragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseMove = useCallback((e: ReactMouseEvent) => {
    if (!dragging.current) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    lastPos.current = { x: e.clientX, y: e.clientY };
    setTranslate((t) => ({ x: t.x + dx, y: t.y + dy }));
  }, []);

  const handleMouseUp = useCallback(() => {
    dragging.current = false;
  }, []);

  const resetView = useCallback(() => {
    setScale(1);
    setTranslate({ x: 0, y: 0 });
  }, []);

  // ESC 关闭
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="mermaid-zoom-overlay" onClick={onClose}>
      <div className="mermaid-zoom-toolbar" onClick={(e) => e.stopPropagation()}>
        <button type="button" onClick={() => setScale((s) => Math.min(s * 1.4, 50))} title="放大">+</button>
        <span className="mermaid-zoom-level">{Math.round(scale * 100)}%</span>
        <button type="button" onClick={() => setScale((s) => Math.max(s / 1.4, 0.1))} title="缩小">−</button>
        <button type="button" onClick={resetView} title="重置">↺</button>
        <button type="button" onClick={onClose} title="关闭 (Esc)">✕</button>
      </div>
      <div
        className="mermaid-zoom-canvas"
        onClick={(e) => e.stopPropagation()}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: dragging.current ? "grabbing" : "grab" }}
      >
        <div
          className="mermaid-zoom-content"
          style={{ transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})` }}
          dangerouslySetInnerHTML={{ __html: svgHtml }}
        />
      </div>
    </div>
  );
}

/** Mermaid 图表渲染块 */
function MermaidBlock({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const uniqueId = useId().replace(/:/g, "_");
  const [svgHtml, setSvgHtml] = useState("");
  const [zoomed, setZoomed] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!containerRef.current || !chart.trim()) return;
    let cancelled = false;
    const elId = `mermaid${uniqueId}`;

    (async () => {
      try {
        const { svg } = await mermaid.render(elId, chart.trim());
        if (!cancelled) {
          setSvgHtml(svg);
          setError(false);
          if (containerRef.current) containerRef.current.innerHTML = svg;
        }
      } catch {
        // 清理 mermaid 注入的错误 DOM 元素
        document.getElementById(`d${elId}`)?.remove();
        if (!cancelled) {
          setError(true);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [chart, uniqueId]);

  // 渲染失败：回退为普通代码块，不显示错误信息
  if (error) {
    return (
      <pre className="md-mermaid-fallback">
        <code>{chart}</code>
      </pre>
    );
  }

  return (
    <>
      <div className="md-mermaid md-mermaid-zoomable">
        <div ref={containerRef} />
        {svgHtml && (
          <button
            type="button"
            className="mermaid-zoom-btn"
            onClick={() => setZoomed(true)}
            title="放大查看"
          >
            ⛶
          </button>
        )}
      </div>
      {zoomed && svgHtml && (
        <MermaidZoomOverlay svgHtml={svgHtml} onClose={() => setZoomed(false)} />
      )}
    </>
  );
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

/**
 * 预处理：检测未被 ```mermaid 包裹的裸 mermaid 语法，自动包裹成代码块。
 * 支持的图表类型关键词参考 mermaid 官方文档。
 */
const MERMAID_KEYWORDS = [
  "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram",
  "erDiagram", "gantt", "pie", "journey", "gitGraph", "mindmap", "timeline",
  "quadrantChart", "sankey", "xychart", "block-beta", "packet-beta",
  "architecture-beta", "kanban",
];
const MERMAID_START_RE = new RegExp(
  `^(${MERMAID_KEYWORDS.join("|")})(?:\\s|[-:;])`, "m"
);

function wrapBareMermaid(content: string): string {
  // 已经在围栏代码块内的不处理
  // 策略：按行扫描，如果一行匹配 mermaid 关键词且不在 ``` 围栏内，
  // 向下收集连续的非空行（或空行后还有缩进/图表语法的行）包裹起来
  const lines = content.split("\n");
  const result: string[] = [];
  let inFence = false;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 追踪围栏状态
    if (/^```/.test(line.trimStart())) {
      inFence = !inFence;
      result.push(line);
      i++;
      continue;
    }

    if (inFence) {
      result.push(line);
      i++;
      continue;
    }

    // 检测裸 mermaid 起始行
    if (MERMAID_START_RE.test(line.trimStart())) {
      // 向下收集图表内容：连续非空行，或空行之后仍有缩进/图表内容
      const block: string[] = [line];
      let j = i + 1;
      while (j < lines.length) {
        const next = lines[j];
        // 遇到新围栏或明显的 markdown 标记（标题、列表前有空行分隔）则停止
        if (/^```/.test(next.trimStart())) break;
        if (next.trim() === "") {
          // 空行：看下一行是否还像图表内容（有缩进、|、-->、---、subgraph 等）
          const peek = lines[j + 1];
          if (peek && /^[\s|]|-->|---|subgraph|end\b|class\s/.test(peek)) {
            block.push(next);
            j++;
            continue;
          }
          break;
        }
        block.push(next);
        j++;
      }
      result.push("```mermaid");
      result.push(...block);
      result.push("```");
      i = j;
      continue;
    }

    result.push(line);
    i++;
  }

  return result.join("\n");
}

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  const processed = wrapBareMermaid(content);
  return (
    <div className={`md-renderer ${className ?? ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code: CodeBlock,
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
