import { useState, useMemo, useCallback, useEffect } from "react";
import * as Diff from "diff";

export interface MarkdownDiffReviewerProps {
  oldContent: string;
  newContent: string;
  onApply: (rebuiltContent: string) => void;
  onRejectAll: () => void;
  saving?: boolean;
}

type HunkStatus = "pending" | "accepted" | "rejected";

interface Hunk {
  id: number;
  removed: string[];
  added: string[];
}

interface ContextBlock {
  type: "context";
  lines: string[];
}

interface HunkBlock {
  type: "hunk";
  hunk: Hunk;
}

type Block = ContextBlock | HunkBlock;

/**
 * Hunk 级交互审阅组件：对 oldContent/newContent 做行级 diff，
 * 将连续的 added/removed 分组为 hunk，每个 hunk 可独立接受/拒绝。
 */
export function MarkdownDiffReviewer({
  oldContent,
  newContent,
  onApply,
  onRejectAll,
  saving = false,
}: MarkdownDiffReviewerProps) {
  const { blocks, hunkCount } = useMemo(() => {
    const changes = Diff.diffLines(oldContent || "", newContent || "");
    const result: Block[] = [];
    let hunkId = 0;
    let pendingRemoved: string[] = [];
    let pendingAdded: string[] = [];

    const flushHunk = () => {
      if (pendingRemoved.length > 0 || pendingAdded.length > 0) {
        result.push({
          type: "hunk",
          hunk: { id: hunkId++, removed: [...pendingRemoved], added: [...pendingAdded] },
        });
        pendingRemoved = [];
        pendingAdded = [];
      }
    };

    for (const part of changes) {
      const lines = part.value.split("\n");
      // diffLines trailing newline
      if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();

      if (part.added) {
        pendingAdded.push(...lines);
      } else if (part.removed) {
        pendingRemoved.push(...lines);
      } else {
        flushHunk();
        result.push({ type: "context", lines });
      }
    }
    flushHunk();

    return { blocks: result, hunkCount: hunkId };
  }, [oldContent, newContent]);

  const [statuses, setStatuses] = useState<HunkStatus[]>(() =>
    Array(hunkCount).fill("pending")
  );

  // props 变化时重置 statuses
  useEffect(() => {
    setStatuses(Array(hunkCount).fill("pending"));
  }, [hunkCount]);

  const setHunkStatus = (id: number, status: HunkStatus) => {
    setStatuses((prev) => {
      const next = [...prev];
      next[id] = status;
      return next;
    });
  };

  const acceptAll = () => {
    setStatuses(Array(hunkCount).fill("accepted"));
  };

  const rejectAll = () => {
    setStatuses(Array(hunkCount).fill("rejected"));
  };

  const counts = useMemo(() => {
    let accepted = 0, rejected = 0, pending = 0;
    for (const s of statuses) {
      if (s === "accepted") accepted++;
      else if (s === "rejected") rejected++;
      else pending++;
    }
    return { accepted, rejected, pending };
  }, [statuses]);

  const handleApply = () => {
    // 每次点击时实时重建，避免闭包缓存问题
    // pending 状态的 hunk 视为接受（用户点击应用即表示同意剩余变更）
    const parts: string[] = [];
    for (const block of blocks) {
      if (block.type === "context") {
        parts.push(block.lines.join("\n"));
      } else {
        const st = statuses[block.hunk.id];
        if (st === "rejected") {
          parts.push(block.hunk.removed.join("\n"));
        } else {
          // accepted 或 pending → 采用新内容
          parts.push(block.hunk.added.join("\n"));
        }
      }
    }
    onApply(parts.join("\n"));
  };

  const handleRejectAll = useCallback(() => {
    onRejectAll();
  }, [onRejectAll]);

  // 如果没有任何变更 hunk
  if (hunkCount === 0) {
    return (
      <div className="diff-reviewer-toolbar">
        <span>文档无变更</span>
        <button type="button" className="secondary" onClick={handleRejectAll}>关闭</button>
      </div>
    );
  }

  return (
    <div className="req-doc-review" style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      {/* 工具栏 */}
      <div className="diff-reviewer-toolbar">
        <div className="diff-reviewer-stats">
          <span className="diff-reviewer-stat accepted">已接受 {counts.accepted}</span>
          <span className="diff-reviewer-stat rejected">已拒绝 {counts.rejected}</span>
          <span className="diff-reviewer-stat pending">待决 {counts.pending}</span>
        </div>
        <div className="diff-reviewer-actions">
          <button type="button" className="secondary xs" onClick={acceptAll}>接受全部</button>
          <button type="button" className="secondary xs" onClick={rejectAll}>拒绝全部</button>
          <button type="button" className="primary" onClick={handleApply} disabled={saving}>
            {saving ? "保存中…" : "应用选择"}
          </button>
          <button type="button" className="secondary" onClick={handleRejectAll}>拒绝变更</button>
        </div>
      </div>

      {/* Diff 内容 — 使用 div 而非 pre，避免交互元素在 pre 中无法点击 */}
      <div
        className="diff-reviewer-content"
        style={{
          flex: 1,
          overflow: "auto",
          margin: 0,
          padding: "0.75rem 1rem",
          fontSize: "0.875rem",
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
        }}
      >
        {blocks.map((block, bi) => {
          if (block.type === "context") {
            return (
              <div key={`ctx-${bi}`}>
                {block.lines.map((line, li) => (
                  <div key={li} className="diff-unchanged" style={{ padding: "0 0.25rem", margin: "0 -0.25rem" }}>
                    <span aria-hidden>  </span>{line || " "}
                  </div>
                ))}
              </div>
            );
          }

          const hunk = block.hunk;
          const status = statuses[hunk.id] ?? "pending";

          return (
            <div
              key={`hunk-${hunk.id}`}
              className={`diff-hunk-block ${status}`}
            >
              <div className="diff-hunk-actions">
                <button
                  type="button"
                  className={`diff-hunk-btn accept${status === "accepted" ? " active" : ""}`}
                  onClick={(e) => { e.stopPropagation(); setHunkStatus(hunk.id, status === "accepted" ? "pending" : "accepted"); }}
                  title="接受"
                >
                  ✓
                </button>
                <button
                  type="button"
                  className={`diff-hunk-btn reject${status === "rejected" ? " active" : ""}`}
                  onClick={(e) => { e.stopPropagation(); setHunkStatus(hunk.id, status === "rejected" ? "pending" : "rejected"); }}
                  title="拒绝"
                >
                  ✗
                </button>
              </div>
              {hunk.removed.map((line, li) => (
                <div
                  key={`r-${li}`}
                  className="diff-removed"
                  style={{ padding: "0 0.25rem", margin: "0 -0.25rem", borderRadius: 2, backgroundColor: "rgba(248, 81, 73, 0.2)", color: "#f85149" }}
                >
                  <span aria-hidden>− </span>{line || " "}
                </div>
              ))}
              {hunk.added.map((line, li) => (
                <div
                  key={`a-${li}`}
                  className="diff-added"
                  style={{ padding: "0 0.25rem", margin: "0 -0.25rem", borderRadius: 2, backgroundColor: "rgba(63, 185, 80, 0.2)", color: "#3fb950" }}
                >
                  <span aria-hidden>+ </span>{line || " "}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
