import * as Diff from "diff";

export interface MarkdownDiffRendererProps {
  oldContent: string;
  newContent: string;
  className?: string;
}

/**
 * 基于 diff 库对两段 Markdown 做行级 diff，红（删除）/绿（新增）/灰（未变）展示。
 * 用于需求文档版本对比或 Agent/工作流生成内容与当前文档的变更查看。
 */
export function MarkdownDiffRenderer({
  oldContent,
  newContent,
  className = "",
}: MarkdownDiffRendererProps) {
  const changes = Diff.diffLines(oldContent || "", newContent || "");
  const lines: { kind: "removed" | "added" | "unchanged"; text: string }[] = [];
  for (const part of changes) {
    const kind = part.added ? "added" : part.removed ? "removed" : "unchanged";
    const text = part.value;
    const split = text.split("\n");
    // 去掉末尾空行（diffLines 常带 trailing newline）
    if (split.length > 1 && split[split.length - 1] === "") split.pop();
    for (const line of split) {
      lines.push({ kind, text: line });
    }
  }

  return (
    <pre
      className={`markdown-diff ${className}`.trim()}
      style={{
        margin: 0,
        padding: "0.75rem 1rem",
        fontSize: "0.875rem",
        lineHeight: 1.6,
        overflow: "auto",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
      }}
    >
      {lines.map((line, i) => (
        <div
          key={i}
          className={
            line.kind === "removed"
              ? "diff-removed"
              : line.kind === "added"
                ? "diff-added"
                : "diff-unchanged"
          }
          style={{
            padding: "0 0.25rem",
            margin: "0 -0.25rem",
            borderRadius: 2,
            ...(line.kind === "removed"
              ? { backgroundColor: "rgba(248, 81, 73, 0.2)", color: "#f85149" }
              : line.kind === "added"
                ? { backgroundColor: "rgba(63, 185, 80, 0.2)", color: "#3fb950" }
                : { color: "var(--color-fg-muted, #8b949e)" }),
          }}
        >
          {line.kind === "removed" && <span aria-hidden>− </span>}
          {line.kind === "added" && <span aria-hidden>+ </span>}
          {line.kind === "unchanged" && <span aria-hidden>  </span>}
          {line.text || " "}
        </div>
      ))}
    </pre>
  );
}
