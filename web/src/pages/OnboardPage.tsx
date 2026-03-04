import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, type ProjectCreate } from "../api/client";
import { GlowInput } from "../components/GlowInput";
import { FlowButton } from "../components/FlowButton";

export function OnboardPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [businessLine, setBusinessLine] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const body: ProjectCreate = {
        name: name.trim(),
        repo_path: repoPath.trim() || "",
      };
      const project = await createProject(body);
      setSuccess(true);
      setTimeout(() => navigate(`/projects/${project.id}`), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "校验或接入失败");
    } finally {
      setLoading(false);
    }
  };

  const canSubmit = !!name.trim();

  return (
    <div data-testid="page-onboard">
      <h1 className="page-title">创建项目并添加仓库</h1>

      <div className="card" style={{ maxWidth: 520 }}>
        <div className="form-row">
          <label htmlFor="onboard-name">项目名称</label>
          <GlowInput
            id="onboard-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：订单中台"
            disabled={loading}
          />
        </div>
        <div className="form-row">
          <label htmlFor="onboard-business">业务线（可选）</label>
          <GlowInput
            id="onboard-business"
            value={businessLine}
            onChange={(e) => setBusinessLine(e.target.value)}
            placeholder="选填"
            disabled={loading}
          />
        </div>
        <div className="form-row">
          <label htmlFor="onboard-repo">Git 仓库 URL 或本地路径（可选）</label>
          <GlowInput
            id="onboard-repo"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="可留空，后续在项目详情配置"
            disabled={loading}
          />
        </div>
        <div className="form-row">
          <label htmlFor="onboard-token">Token 鉴权（可选）</label>
          <GlowInput
            id="onboard-token"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="私有仓库可填 Token"
            disabled={loading}
          />
        </div>
        {error && <div className="result error" data-testid="onboard-error">{error}</div>}
        {success && (
          <div className="result" data-testid="onboard-success">
            创建成功
          </div>
        )}
        <FlowButton
          onClick={handleSubmit}
          loading={loading}
          disabled={!canSubmit || success}
          data-testid="onboard-submit"
        >
          校验并接入资产
        </FlowButton>
      </div>
    </div>
  );
}
