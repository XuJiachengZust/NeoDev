import { useEffect, useState } from "react";
import {
  listProductProjects,
  listCommits,
  type Project,
  type Commit,
} from "../api/client";

interface CommitSearchModalProps {
  productId: number;
  onSelect: (commitIds: number[]) => void;
  onClose: () => void;
}

export function CommitSearchModal({ productId, onSelect, onClose }: CommitSearchModalProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    listProductProjects(productId).then(setProjects).catch(() => {});
  }, [productId]);

  useEffect(() => {
    if (!selectedProject) {
      setCommits([]);
      return;
    }
    setLoading(true);
    listCommits(selectedProject)
      .then(setCommits)
      .catch(() => setCommits([]))
      .finally(() => setLoading(false));
  }, [selectedProject]);

  const filtered = searchText
    ? commits.filter(
        (c) =>
          c.message?.toLowerCase().includes(searchText.toLowerCase()) ||
          c.commit_sha.includes(searchText)
      )
    : commits;

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ margin: 0 }}>搜索提交</h3>
          <button type="button" className="modal-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="flex gap-12 mb-16">
          <select
            className="input-select"
            value={selectedProject ?? ""}
            onChange={(e) => setSelectedProject(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">选择项目</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <input
            className="glow-input flex-1"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="搜索提交信息或 SHA..."
          />
        </div>

        {loading && <div className="loading-state">加载中...</div>}

        <div className="flex-col gap-4" style={{ maxHeight: 300, overflowY: "auto" }}>
          {filtered.map((c) => (
            <label
              key={c.id}
              className="flex-center gap-8"
              style={{
                padding: "6px 8px",
                borderRadius: 4,
                cursor: "pointer",
                background: selected.has(c.id) ? "rgba(0, 240, 255, 0.08)" : "transparent",
              }}
            >
              <input
                type="checkbox"
                checked={selected.has(c.id)}
                onChange={() => toggle(c.id)}
              />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--color-primary)" }}>
                {c.commit_sha.slice(0, 8)}
              </span>
              <span className="flex-1 text-caption">
                {c.message?.slice(0, 80)}
              </span>
            </label>
          ))}
          {!loading && filtered.length === 0 && selectedProject && (
            <div className="empty-state">无匹配提交</div>
          )}
        </div>

        <div className="flex gap-12 mt-16" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="secondary" onClick={onClose}>
            取消
          </button>
          <button
            type="button"
            className="primary"
            disabled={selected.size === 0}
            onClick={() => onSelect(Array.from(selected))}
          >
            确认选择 ({selected.size})
          </button>
        </div>
      </div>
    </div>
  );
}
