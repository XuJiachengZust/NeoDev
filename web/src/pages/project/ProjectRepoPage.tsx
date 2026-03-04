import { useState } from "react";
import { createVersion, listBranches, listVersions, updateProject } from "../../api/client";
import { FlowButton } from "../../components/FlowButton";
import { useProjectPageContext } from "./ProjectLayoutPage";

function isRepoUrl(path: string): boolean {
  const p = (path || "").trim();
  return p.startsWith("http://") || p.startsWith("https://") || p.startsWith("git@");
}

export function ProjectRepoPage() {
  const { projectId, project, reloadProject } = useProjectPageContext();
  const [repoPathInput, setRepoPathInput] = useState(project.repo_path || "");
  const [repoUsername, setRepoUsername] = useState("");
  const [repoPassword, setRepoPassword] = useState("");
  const [savingRepo, setSavingRepo] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSaveRepo = async () => {
    setSavingRepo(true);
    setError(null);
    setSuccess(null);
    try {
      await updateProject(projectId, { repo_path: repoPathInput.trim() });
      await reloadProject();
      setSuccess("仓库配置已保存");
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存仓库配置失败");
    } finally {
      setSavingRepo(false);
    }
  };

  const handleScanRepo = async () => {
    if (!repoPathInput.trim()) return;
    setScanning(true);
    setError(null);
    setSuccess(null);
    try {
      const opts = isRepoUrl(repoPathInput)
        ? {
            repo_url: repoPathInput,
            username: repoUsername.trim() || undefined,
            password: repoPassword || undefined,
          }
        : { path: repoPathInput };
      const { branches } = await listBranches(opts);
      const existing = new Set(
        (await listVersions(projectId)).map((v) => v.branch).filter((b): b is string => !!b)
      );
      for (const branch of branches) {
        if (existing.has(branch)) continue;
        await createVersion(projectId, { branch, version_name: null });
      }
      setSuccess(`扫描完成，识别 ${branches.length} 个分支`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "扫描仓库失败");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="card" data-testid="project-repo-page">
      <h3>仓库配置</h3>
      <div className="form-row">
        <label htmlFor="project-repo-config">仓库 URL 或本地路径</label>
        <input
          id="project-repo-config"
          className="glow-input"
          value={repoPathInput}
          onChange={(e) => setRepoPathInput(e.target.value)}
          placeholder="http://gitlab.example.com/group/repo.git 或 D:/repo"
        />
      </div>
      {isRepoUrl(repoPathInput) && (
        <>
          <div className="form-row">
            <label htmlFor="project-repo-username">Git 用户名（可选，私有仓库必填）</label>
            <input
              id="project-repo-username"
              className="glow-input"
              type="text"
              value={repoUsername}
              onChange={(e) => setRepoUsername(e.target.value)}
              placeholder="GitLab 用户名或 Token 用户名"
              autoComplete="username"
            />
          </div>
          <div className="form-row">
            <label htmlFor="project-repo-password">密码 / Token（可选）</label>
            <input
              id="project-repo-password"
              className="glow-input"
              type="password"
              value={repoPassword}
              onChange={(e) => setRepoPassword(e.target.value)}
              placeholder="密码或 Personal Access Token"
              autoComplete="current-password"
            />
          </div>
        </>
      )}
      <div style={{ display: "flex", gap: 12 }}>
        <button type="button" className="secondary" onClick={handleSaveRepo} disabled={savingRepo}>
          {savingRepo ? "保存中..." : "保存仓库配置"}
        </button>
        <FlowButton onClick={handleScanRepo} loading={scanning} disabled={!repoPathInput.trim()}>
          扫描仓库并更新版本
        </FlowButton>
      </div>
      {error && <div className="result error">{error}</div>}
      {success && <div className="result">{success}</div>}
    </div>
  );
}
