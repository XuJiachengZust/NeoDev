import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useProductPageContext } from "./ProductLayoutPage";
import {
  getProject,
  updateProject,
  listProjectBranches,
  listProductVersions,
  listVersionBranches,
  listVersions,
  listCommitsByVersion,
  syncCommitsForVersion,
  getPreprocessStatus,
  postPreprocess,
  createImpactAnalysis,
  bindRequirementCommitsProduct,
  unbindRequirementCommitsProduct,
  listProductRequirementsTreeWithCounts,
  listRequirementCommits,
  createVersion,
  type Project,
  type ProductVersion,
  type ProductRequirementWithCounts,
  type Version,
  type Commit,
  type PreprocessStatusItem,
} from "../../api/client";
import { useVirtualizer } from "@tanstack/react-virtual";
import { FlowButton } from "../../components/FlowButton";
import { RequirementSelectorModal } from "../../components/RequirementSelectorModal";
import { Toast } from "../../components/Toast";

export function ProductProjectDetailPage() {
  const { productId, product } = useProductPageContext();
  const { projectId: pid } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectId = pid ? Number(pid) : NaN;
  const urlVersionId = searchParams.get("versionId");

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 版本选择器
  const [productVersions, setProductVersions] = useState<ProductVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [currentBranch, setCurrentBranch] = useState<string | null>(null);

  // 仓库配置弹窗
  const [showRepoModal, setShowRepoModal] = useState(false);
  const [repoPathInput, setRepoPathInput] = useState("");
  const [repoUsername, setRepoUsername] = useState("");
  const [repoPassword, setRepoPassword] = useState("");
  const [savingRepo, setSavingRepo] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // 同步&AI 分析
  const [syncing, setSyncing] = useState(false);
  const [preprocessStatus, setPreprocessStatus] = useState<PreprocessStatusItem | null>(null);
  const [preprocessLoading, setPreprocessLoading] = useState(false);

  // 提交列表 & 筛选
  const [commits, setCommits] = useState<Commit[]>([]);
  const [commitsLoading, setCommitsLoading] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [filterIdInput, setFilterIdInput] = useState("");

  // 提交多选 & 操作
  const [selectedCommits, setSelectedCommits] = useState<Set<number>>(new Set());
  const [actionLoading, setActionLoading] = useState(false);
  const [showReqModal, setShowReqModal] = useState(false);

  // 项目的内部 version（对应分支）
  const [projectVersion, setProjectVersion] = useState<Version | null>(null);

  // （仓库配置已改为弹窗形式，不再使用折叠）

  // 需求完成情况
  const [reqWithCounts, setReqWithCounts] = useState<ProductRequirementWithCounts[]>([]);
  const [reqCountsLoading, setReqCountsLoading] = useState(false);

  // Toast 通知
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const loadProject = useCallback(async () => {
    if (!Number.isFinite(projectId)) return;
    setLoading(true);
    setError(null);
    try {
      const [proj, pVersions] = await Promise.all([
        getProject(projectId),
        listProductVersions(productId),
      ]);
      setProject(proj);
      setRepoPathInput(proj.repo_url || "");
      setRepoUsername(proj.repo_username ?? "");
      setProductVersions(pVersions);

      // 优先使用 URL 参数预选版本，否则选择第一个 developing 版本
      if (pVersions.length > 0 && selectedVersionId == null) {
        const fromUrl = urlVersionId ? pVersions.find((v) => v.id === Number(urlVersionId)) : null;
        const dev = fromUrl || pVersions.find((v) => v.status === "developing") || pVersions[0];
        setSelectedVersionId(dev.id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载项目失败");
    } finally {
      setLoading(false);
    }
  }, [projectId, productId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  // 加载版本-分支映射 & 确定当前项目的分支
  useEffect(() => {
    if (!selectedVersionId || !Number.isFinite(projectId)) return;
    setSelectedCommits(new Set());
    let cancelled = false;

    (async () => {
      try {
        const branches = await listVersionBranches(productId, selectedVersionId);
        if (cancelled) return;
        const match = branches.find((b) => b.project_id === projectId);
        setCurrentBranch(match?.branch ?? null);

        // 查找项目内部 version 对应这个分支，不存在则自动创建
        if (match?.branch) {
          const projectVersions = await listVersions(projectId);
          let pv = projectVersions.find((v) => v.branch === match.branch) ?? null;

          // 自动创建缺失的项目级 version
          if (!pv) {
            try {
              pv = await createVersion(projectId, { branch: match.branch });
            } catch {
              // 409 duplicate_branch 说明并发创建，重新获取
              const retry = await listVersions(projectId);
              pv = retry.find((v) => v.branch === match.branch) ?? null;
            }
          }
          if (cancelled) return;
          setProjectVersion(pv);

          if (pv) {
            // 加载提交 + 预处理状态
            setCommitsLoading(true);
            const [cmts, preprocessResp] = await Promise.all([
              listCommitsByVersion(projectId, pv.id),
              getPreprocessStatus(projectId, match.branch).catch(() => null),
            ]);
            if (!cancelled) {
              setCommits(cmts);
              if (preprocessResp && "status" in preprocessResp) {
                setPreprocessStatus(preprocessResp as PreprocessStatusItem);
              } else if (preprocessResp && "items" in preprocessResp) {
                const items = (preprocessResp as { items: PreprocessStatusItem[] }).items;
                setPreprocessStatus(items.find((i) => i.branch === match.branch) ?? null);
              }
              setCommitsLoading(false);
            }
            // 重置筛选
            setFilterText("");
            setFilterDateFrom("");
            setFilterDateTo("");
            setFilterIdInput("");
          } else {
            setCommits([]);
            setPreprocessStatus(null);
          }
        } else {
          setProjectVersion(null);
          setCommits([]);
          setPreprocessStatus(null);
        }
      } catch {
        if (!cancelled) {
          setCurrentBranch(null);
          setProjectVersion(null);
          setCommits([]);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [productId, projectId, selectedVersionId]);

  // 加载需求完成情况
  const loadReqCounts = useCallback(async () => {
    if (!selectedVersionId) {
      setReqWithCounts([]);
      return;
    }
    setReqCountsLoading(true);
    try {
      const data = await listProductRequirementsTreeWithCounts(productId, selectedVersionId);
      setReqWithCounts(data);
    } catch {
      setReqWithCounts([]);
    } finally {
      setReqCountsLoading(false);
    }
  }, [productId, selectedVersionId]);

  useEffect(() => {
    loadReqCounts();
  }, [loadReqCounts]);

  // 加载提交（带服务端日期过滤）
  const loadCommits = useCallback(async (pv?: Version | null) => {
    const ver = pv ?? projectVersion;
    if (!ver) return;
    setCommitsLoading(true);
    try {
      const params: { message?: string; committed_at_from?: string; committed_at_to?: string; id?: number; sha?: string } = {};
      if (filterDateFrom) params.committed_at_from = filterDateFrom;
      if (filterDateTo) params.committed_at_to = filterDateTo;
      const cmts = await listCommitsByVersion(projectId, ver.id, params);
      setCommits(cmts);
    } catch {
      setCommits([]);
    } finally {
      setCommitsLoading(false);
    }
  }, [projectId, projectVersion, filterDateFrom, filterDateTo]);

  // 客户端筛选：消息/SHA/ID
  const filteredCommits = useMemo(() => {
    let list = commits;
    const text = filterText.trim().toLowerCase();
    if (text) {
      list = list.filter(
        (c) =>
          (c.message ?? "").toLowerCase().includes(text) ||
          c.commit_sha.toLowerCase().includes(text) ||
          (c.author ?? "").toLowerCase().includes(text)
      );
    }
    const idNum = filterIdInput.trim() ? Number(filterIdInput.trim()) : NaN;
    if (Number.isFinite(idNum)) {
      list = list.filter((c) => c.id === idNum);
    }
    return list;
  }, [commits, filterText, filterIdInput]);

  // 虚拟滚动
  const scrollRef = useRef<HTMLDivElement>(null);
  const ROW_H = 34;
  const virtualizer = useVirtualizer({
    count: filteredCommits.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_H,
    overscan: 20,
  });

  // 记录确认后要执行的动作：save 或 scan
  const [confirmAction, setConfirmAction] = useState<"save" | "scan">("save");

  const handleSaveRepo = () => {
    setConfirmAction("save");
    setShowConfirmDialog(true);
  };

  const handleScanRepo = () => {
    if (!repoPathInput.trim()) return;
    setConfirmAction("scan");
    setShowConfirmDialog(true);
  };

  const doConfirmedAction = async () => {
    setShowConfirmDialog(false);
    if (confirmAction === "scan") {
      doScanRepo();
    } else {
      doSaveRepo();
    }
  };

  const doSaveRepo = async () => {
    setSavingRepo(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: Parameters<typeof updateProject>[1] = {
        repo_path: repoPathInput.trim(),
        repo_username: repoUsername.trim() || null,
        repo_password: repoPassword || null,
      };
      await updateProject(projectId, payload);
      await loadProject();
      setSuccess("仓库配置已保存");
      setShowRepoModal(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存仓库配置失败");
    } finally {
      setSavingRepo(false);
    }
  };

  const doScanRepo = async () => {
    setScanning(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: Parameters<typeof updateProject>[1] = {
        repo_path: repoPathInput.trim(),
        repo_username: repoUsername.trim() || null,
        repo_password: repoPassword || null,
      };
      await updateProject(projectId, payload);
      const branches = await listProjectBranches(projectId);
      await loadProject();
      setSuccess(`扫描完成，识别 ${branches.length} 个分支`);
      setShowRepoModal(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "扫描仓库失败");
    } finally {
      setScanning(false);
    }
  };

  const handleSync = async () => {
    if (!projectVersion) return;
    setSyncing(true);
    setError(null);
    try {
      await syncCommitsForVersion(projectId, projectVersion.id);
      await loadCommits();
      setSuccess("同步完成");
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步提交失败");
    } finally {
      setSyncing(false);
    }
  };

  const handlePreprocess = async () => {
    if (!currentBranch) return;
    setPreprocessLoading(true);
    setError(null);
    try {
      await postPreprocess(projectId, currentBranch, false);
      setSuccess("AI 分析已触发");
    } catch (e) {
      setError(e instanceof Error ? e.message : "触发 AI 分析失败");
    } finally {
      setPreprocessLoading(false);
    }
  };

  const toggleCommit = (id: number) => {
    setSelectedCommits((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAllFiltered = () => {
    const allIds = new Set(filteredCommits.map((c) => c.id));
    const allSelected = filteredCommits.every((c) => selectedCommits.has(c.id));
    if (allSelected) {
      setSelectedCommits((prev) => {
        const next = new Set(prev);
        allIds.forEach((id) => next.delete(id));
        return next;
      });
    } else {
      setSelectedCommits((prev) => new Set([...prev, ...allIds]));
    }
  };

  const handleImpactAnalysis = async () => {
    if (selectedCommits.size === 0) return;
    setActionLoading(true);
    setError(null);
    try {
      await createImpactAnalysis(projectId, { commit_ids: Array.from(selectedCommits) });
      setSuccess("影响面分析已创建");
      setSelectedCommits(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建影响面分析失败");
    } finally {
      setActionLoading(false);
    }
  };

  const handleBindRequirement = async (reqId: number) => {
    setShowReqModal(false);
    if (selectedCommits.size === 0) return;
    setActionLoading(true);
    setError(null);
    try {
      await bindRequirementCommitsProduct(productId, reqId, Array.from(selectedCommits));
      setToast({ message: "需求绑定成功", type: "success" });
      setSelectedCommits(new Set());
      loadReqCounts();
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : "绑定需求失败", type: "error" });
    } finally {
      setActionLoading(false);
    }
  };

  if (!Number.isFinite(projectId)) return <div className="result error">无效项目</div>;
  if (loading) return <div className="loading-state">加载中...</div>;
  if (!project) return <div className="result error">{error ?? "项目不存在"}</div>;

  const hasBranch = !!(currentBranch && projectVersion);

  return (
    <div data-testid="page-product-project-detail" style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* 顶部工具栏：面包屑 + 版本选择 + 操作按钮 */}
      <div className="card mb-16" style={{ flexShrink: 0 }}>
        <div className="flex-center gap-12 flex-wrap">
          <button type="button" className="secondary sm" onClick={() => navigate(`/products/${productId}/projects`)}>
            {product.name}
          </button>
          <span className="text-muted">/</span>
          <span className="text-bold">{project.name}</span>
          <span className="flex-1" />
          <button
            type="button"
            className="secondary sm"
            onClick={() => {
              setRepoPathInput(project.repo_url || "");
              setRepoUsername(project.repo_username ?? "");
              setRepoPassword("");
              setShowRepoModal(true);
            }}
          >
            配置仓库
          </button>
          {productVersions.length > 0 && (
            <>
              <select
                className="input-select"
                value={selectedVersionId ?? ""}
                onChange={(e) => setSelectedVersionId(e.target.value ? Number(e.target.value) : null)}
                style={{ minWidth: "8rem", padding: "6px 10px", fontSize: 13 }}
              >
                {productVersions.map((v) => (
                  <option key={v.id} value={v.id}>{v.version_name}</option>
                ))}
              </select>
              {currentBranch && (
                <span className="text-caption" style={{ color: "var(--color-primary)" }}>{currentBranch}</span>
              )}
            </>
          )}
          {hasBranch && (
            <>
              <button type="button" className="secondary sm" onClick={handleSync} disabled={syncing}>
                {syncing ? "同步中..." : "同步提交"}
              </button>
              <button
                type="button"
                className="secondary sm"
                onClick={handlePreprocess}
                disabled={preprocessLoading || preprocessStatus?.status === "running"}
              >
                {preprocessLoading || preprocessStatus?.status === "running" ? "分析中..." : "AI 分析"}
              </button>
              {preprocessStatus && (
                <span className="text-caption text-muted">({preprocessStatus.status})</span>
              )}
            </>
          )}
        </div>
      </div>

      {error && <div className="result error mb-16" style={{ flexShrink: 0 }}>{error}</div>}
      {success && <div className="result mb-16" style={{ flexShrink: 0 }}>{success}</div>}

      {/* 仓库配置弹窗 */}
      {showRepoModal && (
        <div className="modal-overlay" onClick={() => !savingRepo && !scanning && setShowRepoModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ minWidth: 480, maxWidth: 560 }}>
            <div className="modal-header">
              <h3 style={{ margin: 0 }}>远程仓库配置</h3>
              <button type="button" className="modal-close" onClick={() => setShowRepoModal(false)} disabled={savingRepo || scanning}>&times;</button>
            </div>
            {project.repo_url && (
              <div style={{ marginBottom: 16, padding: "8px 12px", borderRadius: 6, background: "rgba(0, 240, 255, 0.06)", border: "1px solid rgba(0, 240, 255, 0.15)", fontSize: 13 }}>
                <span className="text-muted">当前仓库：</span>
                <span style={{ color: "var(--color-primary)", wordBreak: "break-all" }}>{project.repo_url}</span>
              </div>
            )}
            <div className="form-row">
              <label>远程仓库 URL</label>
              <input className="glow-input" value={repoPathInput} onChange={(e) => setRepoPathInput(e.target.value)} placeholder="http://gitlab.example.com/group/repo.git" />
            </div>
            <div className="form-row">
              <label>Git 用户名（可选）</label>
              <input className="glow-input" type="text" value={repoUsername} onChange={(e) => setRepoUsername(e.target.value)} placeholder="用户名" autoComplete="username" />
            </div>
            <div className="form-row">
              <label>密码 / Token（可选）</label>
              <input className="glow-input" type="password" value={repoPassword} onChange={(e) => setRepoPassword(e.target.value)} placeholder="密码或 Token" autoComplete="current-password" />
            </div>
            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="secondary" onClick={() => setShowRepoModal(false)} disabled={savingRepo || scanning}>取消</button>
              <button type="button" className="secondary" onClick={handleSaveRepo} disabled={savingRepo || scanning || !repoPathInput.trim()}>{savingRepo ? "保存中..." : "保存配置"}</button>
              <FlowButton onClick={handleScanRepo} loading={scanning} disabled={!repoPathInput.trim() || savingRepo}>扫描分支</FlowButton>
            </div>
          </div>
        </div>
      )}

      {/* 确认更新弹窗 */}
      {showConfirmDialog && (
        <div className="modal-overlay" onClick={() => setShowConfirmDialog(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ minWidth: 400, maxWidth: 480 }}>
            <div className="modal-header">
              <h3 style={{ margin: 0, color: "var(--color-alert)" }}>确认更新仓库配置</h3>
              <button type="button" className="modal-close" onClick={() => setShowConfirmDialog(false)}>&times;</button>
            </div>
            <p style={{ margin: "0 0 16px", lineHeight: 1.6 }}>
              更新配置后将重新克隆远程仓库并<strong>覆盖本地仓库与图数据库</strong>，已有的 <strong>AI 分析结果将丢失</strong>。
            </p>
            <p style={{ margin: "0 0 20px", color: "var(--color-text-muted)", fontSize: 13 }}>
              是否确定更新？
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="secondary" onClick={() => setShowConfirmDialog(false)}>取消</button>
              <button
                type="button"
                className="primary"
                style={{ background: "var(--color-alert)" }}
                onClick={doConfirmedAction}
              >
                确认更新
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 主内容区：两列布局 */}
      {hasBranch && (
        <div style={{ flex: 1, minHeight: 0, display: "grid", gridTemplateColumns: "1fr 340px", gap: 16 }}>

      {/* 左列：提交列表 */}
      <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>
          <div className="flex-between mb-8">
            <h3 style={{ margin: 0 }}>提交列表（{currentBranch}）</h3>
            <span className="text-caption text-muted">{filteredCommits.length} / {commits.length}</span>
          </div>

          {/* 筛选栏 */}
          <div className="flex-center gap-8 mb-12 flex-wrap" style={{ fontSize: 13 }}>
            <input
              className="glow-input"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              placeholder="搜索消息 / SHA / 作者"
              style={{ flex: 1, minWidth: 140, padding: "5px 10px", fontSize: 13 }}
            />
            <input
              className="glow-input"
              value={filterIdInput}
              onChange={(e) => setFilterIdInput(e.target.value)}
              placeholder="ID"
              style={{ width: 64, padding: "5px 10px", fontSize: 13 }}
            />
            <input
              type="date"
              className="glow-input"
              value={filterDateFrom}
              onChange={(e) => setFilterDateFrom(e.target.value)}
              style={{ width: 130, padding: "5px 8px", fontSize: 12 }}
              title="起始日期"
            />
            <span className="text-muted">-</span>
            <input
              type="date"
              className="glow-input"
              value={filterDateTo}
              onChange={(e) => setFilterDateTo(e.target.value)}
              style={{ width: 130, padding: "5px 8px", fontSize: 12 }}
              title="截止日期"
            />
            {(filterDateFrom || filterDateTo) && (
              <button type="button" className="secondary xs" onClick={() => loadCommits()}>查询</button>
            )}
            {(filterText || filterDateFrom || filterDateTo || filterIdInput) && (
              <button
                type="button"
                className="secondary xs"
                onClick={() => { setFilterText(""); setFilterDateFrom(""); setFilterDateTo(""); setFilterIdInput(""); loadCommits(); }}
              >清除</button>
            )}
          </div>

          {/* 操作栏 */}
          {selectedCommits.size > 0 && (
            <div
              className="flex-center gap-8 mb-12"
              style={{ padding: "6px 10px", borderRadius: 6, background: "rgba(0, 240, 255, 0.06)", border: "1px solid rgba(0, 240, 255, 0.15)" }}
            >
              <span className="text-caption">已选 {selectedCommits.size} 个</span>
              <span className="flex-1" />
              <button type="button" className="primary sm" disabled={actionLoading} onClick={handleImpactAnalysis}>
                {actionLoading ? "处理中..." : "影响面分析"}
              </button>
              <button type="button" className="secondary sm" disabled={actionLoading} onClick={() => setShowReqModal(true)}>绑定需求</button>
              <button type="button" className="secondary sm" onClick={() => setSelectedCommits(new Set())}>取消</button>
            </div>
          )}

          {commitsLoading ? (
            <div className="loading-state">加载中...</div>
          ) : commits.length === 0 ? (
            <div className="text-muted" style={{ padding: "24px 0", textAlign: "center" }}>暂无提交，请先同步</div>
          ) : filteredCommits.length === 0 ? (
            <div className="text-muted" style={{ padding: "24px 0", textAlign: "center" }}>无匹配提交</div>
          ) : (
            <>
              {/* 表头 */}
              <div
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 4px", borderBottom: "1px solid rgba(255,255,255,0.08)", marginBottom: 2 }}
              >
                <input
                  type="checkbox"
                  checked={filteredCommits.length > 0 && filteredCommits.every((c) => selectedCommits.has(c.id))}
                  onChange={toggleAllFiltered}
                />
                <span className="text-caption text-muted" style={{ minWidth: 56 }}>SHA</span>
                <span className="text-caption text-muted flex-1">消息</span>
                <span className="text-caption text-muted" style={{ minWidth: 56 }}>作者</span>
                <span className="text-caption text-muted" style={{ minWidth: 72 }}>日期</span>
                <span className="text-caption text-muted" style={{ minWidth: 36 }}>ID</span>
              </div>
              {/* 虚拟滚动区 */}
              <div ref={scrollRef} style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
                <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
                  {virtualizer.getVirtualItems().map((vRow) => {
                    const c = filteredCommits[vRow.index];
                    return (
                      <div
                        key={c.id}
                        data-index={vRow.index}
                        ref={virtualizer.measureElement}
                        style={{
                          position: "absolute",
                          top: 0,
                          left: 0,
                          width: "100%",
                          transform: `translateY(${vRow.start}px)`,
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "5px 4px",
                          borderRadius: 4,
                          background: selectedCommits.has(c.id) ? "rgba(0, 240, 255, 0.06)" : "transparent",
                          cursor: "pointer",
                          boxSizing: "border-box",
                        }}
                        onClick={() => toggleCommit(c.id)}
                      >
                        <input type="checkbox" checked={selectedCommits.has(c.id)} onChange={() => toggleCommit(c.id)} onClick={(e) => e.stopPropagation()} />
                        <span className="mono" style={{ minWidth: 56, fontSize: 12, color: "var(--color-primary)" }}>{c.commit_sha.slice(0, 7)}</span>
                        <span className="flex-1" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.message ?? ""}</span>
                        {c.author && <span className="text-caption text-muted" style={{ flexShrink: 0 }}>{c.author}</span>}
                        {c.committed_at && <span className="text-caption text-muted" style={{ flexShrink: 0, fontSize: 11 }}>{c.committed_at.slice(0, 10)}</span>}
                        <span className="text-caption text-muted" style={{ flexShrink: 0, fontSize: 11 }}>#{c.id}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>

      {/* 右列：需求完成情况 */}
      <div className="card" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <h3 style={{ flexShrink: 0 }}>需求完成情况</h3>
          {reqCountsLoading ? (
            <div className="loading-state">加载中...</div>
          ) : reqWithCounts.length === 0 ? (
            <div className="text-muted" style={{ textAlign: "center", padding: "24px 0" }}>
              暂无需求
              {selectedVersionId && (
                <div style={{ marginTop: 8 }}>
                  <a
                    href="#"
                    onClick={(e) => { e.preventDefault(); navigate(`/products/${productId}/versions/${selectedVersionId}/requirements`); }}
                    style={{ color: "var(--color-primary)", fontSize: 13 }}
                  >
                    前往需求管理创建需求
                  </a>
                </div>
              )}
            </div>
          ) : (() => {
            const total = reqWithCounts.length;
            const doneCount = reqWithCounts.filter(
              (r) => r.status === "done" || r.status === "closed"
            ).length;
            const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;
            const epics = reqWithCounts.filter((r) => r.level === "epic");
            const stories = reqWithCounts.filter((r) => r.level === "story");
            const tasks = reqWithCounts.filter((r) => r.level === "task");
            return (
              <>
                <div className="stats mb-12" style={{ flexShrink: 0 }}>
                  <div className="stat">总需求: {total}</div>
                  <div className="stat">已完成: {doneCount}</div>
                  <div className="stat">完成率: {pct}%</div>
                </div>
                <div
                  style={{
                    height: 4,
                    borderRadius: 2,
                    background: "rgba(255,255,255,0.08)",
                    marginBottom: 12,
                    overflow: "hidden",
                    flexShrink: 0,
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${pct}%`,
                      background: "var(--color-primary)",
                      borderRadius: 2,
                      transition: "width 0.3s",
                    }}
                  />
                </div>
                <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
                <ReqTree
                  epics={epics}
                  stories={stories}
                  tasks={tasks}
                  productId={productId}
                  onUnbind={loadReqCounts}
                  setToast={setToast}
                />
                </div>
              </>
            );
          })()}
        </div>

      </div>
      )}

      {/* 需求选择弹窗 */}
      {showReqModal && selectedVersionId && (
        <RequirementSelectorModal
          productId={productId}
          versionId={selectedVersionId}
          onSelect={handleBindRequirement}
          onClose={() => setShowReqModal(false)}
        />
      )}

      {/* Toast 通知 */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

function ReqTree({
  epics, stories, tasks, productId, onUnbind, setToast,
}: {
  epics: ProductRequirementWithCounts[];
  stories: ProductRequirementWithCounts[];
  tasks: ProductRequirementWithCounts[];
  productId: number;
  onUnbind: () => void;
  setToast: (t: { message: string; type: "success" | "error" } | null) => void;
}) {
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const toggle = (id: number) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });

  const [expandedTaskId, setExpandedTaskId] = useState<number | null>(null);

  const renderTask = (task: ProductRequirementWithCounts) => (
    <ReqCountRow
      key={task.id}
      req={task}
      productId={productId}
      expanded={expandedTaskId === task.id}
      onToggleExpand={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}
      onUnbind={onUnbind}
      setToast={setToast}
    />
  );

  const renderStory = (story: ProductRequirementWithCounts) => {
    const childTasks = tasks.filter((t) => t.parent_id === story.id);
    const isCollapsed = collapsed.has(story.id);
    return (
      <div key={story.id}>
        <div className={`req-tree-item ${story.level}`}>
          {childTasks.length > 0 ? (
            <span
              onClick={() => toggle(story.id)}
              style={{ cursor: "pointer", userSelect: "none", fontSize: 11, width: 16, textAlign: "center", flexShrink: 0 }}
            >
              {isCollapsed ? "+" : "-"}
            </span>
          ) : <span style={{ width: 16, flexShrink: 0 }} />}
          <span className={`req-level-badge ${story.level}`}>{story.level}</span>
          <span className="flex-1">{story.title}</span>
          <span className={`status-badge ${story.status}`}>{story.status}</span>
        </div>
        {!isCollapsed && childTasks.map(renderTask)}
      </div>
    );
  };

  const renderEpic = (epic: ProductRequirementWithCounts) => {
    const childStories = stories.filter((s) => s.parent_id === epic.id);
    const isCollapsed = collapsed.has(epic.id);
    return (
      <div key={epic.id}>
        <div className={`req-tree-item ${epic.level}`}>
          {childStories.length > 0 ? (
            <span
              onClick={() => toggle(epic.id)}
              style={{ cursor: "pointer", userSelect: "none", fontSize: 11, width: 16, textAlign: "center", flexShrink: 0 }}
            >
              {isCollapsed ? "+" : "-"}
            </span>
          ) : <span style={{ width: 16, flexShrink: 0 }} />}
          <span className={`req-level-badge ${epic.level}`}>{epic.level}</span>
          <span className="flex-1">{epic.title}</span>
          <span className={`status-badge ${epic.status}`}>{epic.status}</span>
        </div>
        {!isCollapsed && childStories.map(renderStory)}
      </div>
    );
  };

  return (
    <div className="req-tree">
      {epics.map(renderEpic)}
      {stories
        .filter((s) => !s.parent_id || !epics.some((e) => e.id === s.parent_id))
        .map(renderStory)}
      {tasks
        .filter((t) => !t.parent_id || !stories.some((s) => s.id === t.parent_id))
        .map(renderTask)}
    </div>
  );
}

function ReqCountRow({
  req, productId, expanded, onToggleExpand, onUnbind, setToast,
}: {
  req: ProductRequirementWithCounts;
  productId: number;
  expanded: boolean;
  onToggleExpand: () => void;
  onUnbind: () => void;
  setToast: (t: { message: string; type: "success" | "error" } | null) => void;
}) {
  const [commits, setCommits] = useState<Commit[]>([]);
  const [loading, setLoading] = useState(false);
  const [unbinding, setUnbinding] = useState<number | null>(null);

  useEffect(() => {
    if (!expanded) { setCommits([]); return; }
    setLoading(true);
    listRequirementCommits(productId, req.id)
      .then(setCommits)
      .catch(() => setCommits([]))
      .finally(() => setLoading(false));
  }, [expanded, productId, req.id]);

  const handleUnbind = async (commitId: number) => {
    setUnbinding(commitId);
    try {
      await unbindRequirementCommitsProduct(productId, req.id, [commitId]);
      setCommits((prev) => prev.filter((c) => c.id !== commitId));
      setToast({ message: "已解绑提交", type: "success" });
      onUnbind();
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : "解绑失败", type: "error" });
    } finally {
      setUnbinding(null);
    }
  };

  return (
    <div>
      <div className={`req-tree-item ${req.level}`}>
        <span className={`req-level-badge ${req.level}`}>{req.level}</span>
        <span className="flex-1">{req.title}</span>
        <span className={`status-badge ${req.status}`}>{req.status}</span>
        <span
          className="text-caption"
          onClick={req.commit_count > 0 ? onToggleExpand : undefined}
          style={{
            color: req.commit_count > 0 ? "var(--color-primary)" : "var(--color-text-muted)",
            minWidth: 60,
            textAlign: "right",
            cursor: req.commit_count > 0 ? "pointer" : "default",
            userSelect: "none",
          }}
        >
          {expanded ? "收起" : `${req.commit_count} 个提交`}
        </span>
      </div>
      {expanded && (
        <div style={{ marginLeft: 56, marginBottom: 4 }}>
          {loading ? (
            <div className="text-caption text-muted" style={{ padding: "4px 0" }}>加载中...</div>
          ) : commits.length === 0 ? (
            <div className="text-caption text-muted" style={{ padding: "4px 0" }}>无绑定提交</div>
          ) : commits.map((c) => (
            <div
              key={c.id}
              className="flex-center gap-8"
              style={{ padding: "3px 0", fontSize: 12, borderBottom: "1px solid rgba(255,255,255,0.04)" }}
            >
              <span style={{ color: "var(--color-primary)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
                {c.commit_sha.slice(0, 7)}
              </span>
              <span className="flex-1 text-muted" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {c.message ?? ""}
              </span>
              <button
                type="button"
                className="secondary xs"
                style={{ color: "var(--color-alert)", borderColor: "var(--color-alert)", flexShrink: 0 }}
                disabled={unbinding === c.id}
                onClick={() => handleUnbind(c.id)}
              >
                {unbinding === c.id ? "..." : "解绑"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
