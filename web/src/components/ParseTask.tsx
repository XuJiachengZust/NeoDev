import { useState } from "react";
import { runParse } from "../api/client";

export function ParseTask() {
  const [repoPath, setRepoPath] = useState("");
  const [writeNeo4j, setWriteNeo4j] = useState(true);
  const [stats, setStats] = useState<{ node_count: number; relationship_count: number; file_count: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onParse = async () => {
    setStats(null);
    setError(null);
    setLoading(true);
    try {
      const r = await runParse(repoPath, writeNeo4j);
      setStats({
        node_count: r.node_count,
        relationship_count: r.relationship_count,
        file_count: r.file_count,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card">
      <h2>解析任务</h2>
      <div className="form-row">
        <label>仓库路径（已解析的仓库根）</label>
        <input
          value={repoPath}
          onChange={(e) => setRepoPath(e.target.value)}
          placeholder="例如 D:\repos\my-project"
        />
      </div>
      <div className="form-row">
        <label>
          <input
            type="checkbox"
            checked={writeNeo4j}
            onChange={(e) => setWriteNeo4j(e.target.checked)}
          />
          {" "}写入 Neo4j
        </label>
      </div>
      <button onClick={onParse} disabled={loading || !repoPath.trim()}>
        {loading ? "解析中…" : "执行解析"}
      </button>

      {stats != null && (
        <div className="stats">
          <span className="stat">节点: {stats.node_count}</span>
          <span className="stat">关系: {stats.relationship_count}</span>
          <span className="stat">文件: {stats.file_count}</span>
        </div>
      )}
      {error != null && <div className="result error">{error}</div>}
    </section>
  );
}
