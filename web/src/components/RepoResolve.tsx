import { useState } from "react";
import {
  listBranches,
  ensureRepo,
  runParse,
} from "../api/client";

export function RepoResolve() {
  const [path, setPath] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [gitUsername, setGitUsername] = useState("");
  const [gitPassword, setGitPassword] = useState("");
  const [targetPath, setTargetPath] = useState("");
  const [branches, setBranches] = useState<string[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>("");
  const [repoRoot, setRepoRoot] = useState<string | null>(null);
  const [localRepoRoot, setLocalRepoRoot] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [parseStats, setParseStats] = useState<{
    node_count: number;
    relationship_count: number;
    file_count: number;
  } | null>(null);

  const pathToScan = repoRoot ?? localRepoRoot ?? result;

  const onFetchRemoteBranches = async () => {
    setBranches([]);
    setSelectedBranch("");
    setRepoRoot(null);
    setLocalRepoRoot(null);
    setResult(null);
    setError(null);
    setLoading("branches");
    try {
      const r = await listBranches({
        repo_url: repoUrl || undefined,
        username: gitUsername || undefined,
        password: gitPassword || undefined,
      });
      setBranches(r.branches);
      if (r.branches.length > 0) {
        const defaultBranch =
          r.branches.includes("main") ? "main" : r.branches[0];
        setSelectedBranch(defaultBranch);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };

  const onFetchLocalBranches = async () => {
    setBranches([]);
    setSelectedBranch("");
    setRepoRoot(null);
    setResult(null);
    setError(null);
    setLoading("local-branches");
    try {
      const r = await listBranches({ path: path || undefined });
      setBranches(r.branches);
      const root = r.repo_root ?? null;
      setLocalRepoRoot(root);
      setResult(root);
      if (r.branches.length > 0) {
        const defaultBranch =
          r.branches.includes("main") ? "main" : r.branches[0];
        setSelectedBranch(defaultBranch);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };

  const onEnsure = async () => {
    setResult(null);
    setError(null);
    setParseStats(null);
    setLoading("ensure");
    try {
      const auth =
        gitUsername || gitPassword
          ? { username: gitUsername || undefined, password: gitPassword || undefined }
          : undefined;
      const r = await ensureRepo(repoUrl, targetPath, {
        branch: selectedBranch || undefined,
        ...auth,
      });
      setRepoRoot(r.repo_root);
      setResult(r.repo_root);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };

  const onScan = async () => {
    if (!pathToScan || !selectedBranch) return;
    setError(null);
    setParseStats(null);
    setLoading("parse");
    try {
      const r = await runParse(pathToScan, true, selectedBranch);
      setParseStats({
        node_count: r.node_count,
        relationship_count: r.relationship_count,
        file_count: r.file_count,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };

  return (
    <section className="card">
      <h2>解析仓库（提取分支）· 扫描前需指定分支</h2>

      <h3 className="card-subtitle">远程仓库</h3>
      <div className="form-row">
        <label>仓库 URL</label>
        <input
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/org/repo.git 或 GitLab 私服地址"
        />
      </div>
      <div className="form-row">
        <label>Git 账号（可选，GitLab 私服认证）</label>
        <input
          type="text"
          value={gitUsername}
          onChange={(e) => setGitUsername(e.target.value)}
          placeholder="用户名或 Access Token 用户名"
          autoComplete="username"
        />
      </div>
      <div className="form-row">
        <label>Git 密码（可选）</label>
        <input
          type="password"
          value={gitPassword}
          onChange={(e) => setGitPassword(e.target.value)}
          placeholder="密码或 Personal Access Token"
          autoComplete="current-password"
        />
      </div>
      <button
        onClick={onFetchRemoteBranches}
        disabled={loading !== null || !repoUrl.trim()}
      >
        {loading === "branches" ? "获取中…" : "解析并获取分支列表"}
      </button>

      <h3 className="card-subtitle" style={{ marginTop: "1.5rem" }}>
        本地仓库
      </h3>
      <div className="form-row">
        <label>本地路径</label>
        <input
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="例如 D:\repos\my-project"
        />
      </div>
      <button
        onClick={onFetchLocalBranches}
        disabled={loading !== null || !path.trim()}
      >
        {loading === "local-branches" ? "解析中…" : "解析并获取分支列表"}
      </button>

      {branches.length > 0 && (
        <>
          <div className="form-row">
            <label>选择分支（扫描前必选）</label>
            <select
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="input-select"
            >
              {branches.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          {repoUrl.trim() && (
            <>
              <div className="form-row">
                <label>克隆目标路径</label>
                <input
                  value={targetPath}
                  onChange={(e) => setTargetPath(e.target.value)}
                  placeholder="D:\repos\my-project"
                />
              </div>
              <button
                onClick={onEnsure}
                disabled={
                  loading !== null || !repoUrl.trim() || !targetPath.trim()
                }
              >
                {loading === "ensure" ? "克隆中…" : "克隆该分支"}
              </button>
            </>
          )}

          {localRepoRoot && (
            <div className="result">仓库根: {localRepoRoot}</div>
          )}
        </>
      )}

      {pathToScan != null && (
        <div className="result">
          仓库根: {pathToScan}
          <div style={{ marginTop: "0.5rem" }}>
            <button
              onClick={onScan}
              disabled={loading === "parse" || !selectedBranch}
            >
              {loading === "parse" ? "扫描中…" : "扫描该分支"}
            </button>
            {!selectedBranch && branches.length > 0 && (
              <span className="hint">请先在上方选择分支</span>
            )}
          </div>
          {parseStats != null && (
            <div className="stats">
              <span className="stat">节点: {parseStats.node_count}</span>
              <span className="stat">关系: {parseStats.relationship_count}</span>
              <span className="stat">文件: {parseStats.file_count}</span>
            </div>
          )}
        </div>
      )}
      {error != null && <div className="result error">{error}</div>}
    </section>
  );
}
