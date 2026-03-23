import { useCallback, useEffect, useState } from "react";
import {
  getSplitSuggestions,
  saveSplitSuggestions,
  type SplitSuggestion,
} from "../api/client";

interface Props {
  productId: number;
  requirementId: number;
  level: string;
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
  /** 如果由 SSE 实时推送，可直接传入初始数据 */
  initialSuggestions?: SplitSuggestion[] | null;
}

export function SplitSuggestionsModal({
  productId,
  requirementId,
  level,
  open,
  onClose,
  onSaved,
  initialSuggestions,
}: Props) {
  const [items, setItems] = useState<SplitSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!productId || !requirementId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getSplitSuggestions(productId, requirementId);
      setItems(res.suggestions || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [productId, requirementId]);

  useEffect(() => {
    if (!open) return;
    if (initialSuggestions && initialSuggestions.length > 0) {
      setItems(initialSuggestions);
    } else {
      load();
    }
  }, [open, load, initialSuggestions]);

  const handleChange = (index: number, field: keyof SplitSuggestion, value: string) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, [field]: value } : it)));
  };

  const handleDelete = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAdd = () => {
    setItems((prev) => [...prev, { title: "", goal: "" }]);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const filtered = items.filter((it) => it.title.trim());
      await saveSplitSuggestions(productId, requirementId, filtered);
      setItems(filtered);
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  const childLabel = level === "epic" ? "Story" : "Task";

  return (
    <div className="modal-overlay" onClick={() => !saving && onClose()}>
      <div
        className="modal-content"
        style={{ minWidth: 600, maxWidth: 800, maxHeight: "80vh", display: "flex", flexDirection: "column" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 style={{ margin: 0 }}>{childLabel} 拆分建议</h3>
          <button type="button" className="modal-close" onClick={onClose} disabled={saving}>
            &times;
          </button>
        </div>

        {error && (
          <div className="result error" style={{ margin: "0 0 8px" }}>
            {error}
            <button
              type="button"
              className="secondary xs"
              onClick={() => setError(null)}
              style={{ marginLeft: 8, padding: "2px 8px", fontSize: 11 }}
            >
              关闭
            </button>
          </div>
        )}

        <div style={{ flex: 1, overflowY: "auto", marginBottom: 12 }}>
          {loading ? (
            <div className="loading-state">加载中...</div>
          ) : items.length === 0 ? (
            <div className="empty-state" style={{ padding: 24, textAlign: "center", color: "#888" }}>
              暂无拆分建议
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: "6px 8px", borderBottom: "1px solid #333", width: "40%" }}>
                    标题
                  </th>
                  <th style={{ textAlign: "left", padding: "6px 8px", borderBottom: "1px solid #333" }}>
                    业务目标
                  </th>
                  <th style={{ width: 40, borderBottom: "1px solid #333" }} />
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr key={i}>
                    <td style={{ padding: "4px 8px", verticalAlign: "top" }}>
                      <input
                        type="text"
                        value={item.title}
                        onChange={(e) => handleChange(i, "title", e.target.value)}
                        placeholder={`${childLabel} 标题`}
                        style={{ width: "100%", background: "#1a1a2e", color: "#eee", border: "1px solid #333", borderRadius: 4, padding: "4px 6px" }}
                      />
                    </td>
                    <td style={{ padding: "4px 8px", verticalAlign: "top" }}>
                      <input
                        type="text"
                        value={item.goal}
                        onChange={(e) => handleChange(i, "goal", e.target.value)}
                        placeholder="业务目标描述"
                        style={{ width: "100%", background: "#1a1a2e", color: "#eee", border: "1px solid #333", borderRadius: 4, padding: "4px 6px" }}
                      />
                    </td>
                    <td style={{ padding: "4px 4px", textAlign: "center", verticalAlign: "top" }}>
                      <button
                        type="button"
                        className="secondary xs"
                        onClick={() => handleDelete(i)}
                        title="删除"
                        style={{ padding: "2px 6px", fontSize: 12, color: "#f66" }}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
          <button type="button" className="secondary" onClick={handleAdd}>
            + 新增一条
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="secondary" onClick={onClose} disabled={saving}>
              取消
            </button>
            <button type="button" className="primary" onClick={handleSave} disabled={saving || loading}>
              {saving ? "保存中…" : "保存"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
