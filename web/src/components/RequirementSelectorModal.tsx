import { useEffect, useState } from "react";
import {
  listProductRequirementsTree,
  type ProductRequirement,
} from "../api/client";

interface RequirementSelectorModalProps {
  productId: number;
  versionId: number;
  onSelect: (reqId: number) => void;
  onClose: () => void;
}

const LEVEL_LABELS: Record<string, string> = {
  epic: "Epic",
  story: "Story",
  task: "Task",
};

const LEVEL_INDENT: Record<string, number> = {
  epic: 0,
  story: 24,
  task: 48,
};

export function RequirementSelectorModal({
  productId,
  versionId,
  onSelect,
  onClose,
}: RequirementSelectorModalProps) {
  const [requirements, setRequirements] = useState<ProductRequirement[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    listProductRequirementsTree(productId, versionId)
      .then(setRequirements)
      .catch(() => setRequirements([]))
      .finally(() => setLoading(false));
  }, [productId, versionId]);

  const isTask = (req: ProductRequirement) => req.level === "task";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ margin: 0 }}>选择需求</h3>
          <button type="button" className="modal-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <p className="text-caption text-muted" style={{ margin: "0 0 12px" }}>
          仅支持绑定到 Task 级别需求
        </p>

        {loading && <div className="loading-state">加载中...</div>}

        <div className="flex-col gap-4" style={{ maxHeight: 400, overflowY: "auto" }}>
          {requirements.map((req) => {
            const selectable = isTask(req);
            return (
              <label
                key={req.id}
                className="flex-center gap-8"
                style={{
                  padding: "6px 8px",
                  paddingLeft: 8 + LEVEL_INDENT[req.level],
                  borderRadius: 4,
                  cursor: selectable ? "pointer" : "default",
                  opacity: selectable ? 1 : 0.6,
                  background: selectedId === req.id ? "rgba(0, 240, 255, 0.08)" : "transparent",
                }}
              >
                {selectable ? (
                  <input
                    type="radio"
                    name="requirement"
                    checked={selectedId === req.id}
                    onChange={() => setSelectedId(req.id)}
                  />
                ) : (
                  <span style={{ display: "inline-block", width: 16 }} />
                )}
                <span
                  className="text-caption"
                  style={{
                    color: selectable ? "var(--color-primary)" : "var(--color-text-muted)",
                    minWidth: 40,
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                  }}
                >
                  {LEVEL_LABELS[req.level] ?? req.level}
                </span>
                <span className="flex-1">{req.title}</span>
                <span className="text-caption text-muted">{req.status}</span>
              </label>
            );
          })}
          {!loading && requirements.length === 0 && (
            <div className="empty-state">该版本暂无需求</div>
          )}
        </div>

        <div className="flex gap-12 mt-16" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="secondary" onClick={onClose}>
            取消
          </button>
          <button
            type="button"
            className="primary"
            disabled={selectedId == null}
            onClick={() => selectedId != null && onSelect(selectedId)}
          >
            确认选择
          </button>
        </div>
      </div>
    </div>
  );
}
