const API_BASE = "";

type JsonRequestOptions = Omit<RequestInit, "body"> & {
  body?: object;
};

async function request<T>(
  path: string,
  options: JsonRequestOptions = {}
): Promise<T> {
  const { body, ...rest } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...rest.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error((data as { detail?: string }).detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  return data as T;
}

// --- Impact analysis API types (Phase 5) ---

export interface Project {
  id: number;
  name: string;
  repo_path: string;
  created_at?: string;
  watch_enabled?: boolean;
  neo4j_database?: string | null;
  neo4j_identifier?: string | null;
  repo_username?: string | null;
  repo_password?: string | null;
}

export interface ProjectCreate {
  name: string;
  repo_path: string;
  watch_enabled?: boolean;
  neo4j_database?: string | null;
  neo4j_identifier?: string | null;
  repo_username?: string | null;
  repo_password?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  repo_path?: string;
  watch_enabled?: boolean;
  neo4j_database?: string | null;
  neo4j_identifier?: string | null;
  repo_username?: string | null;
  repo_password?: string | null;
}

export interface Version {
  id: number;
  project_id: number;
  branch?: string | null;
  version_name?: string | null;
  created_at?: string;
  last_parsed_commit?: string | null;
}

export interface VersionCreate {
  branch?: string | null;
  version_name?: string | null;
}

export interface Requirement {
  id: number;
  project_id: number;
  title: string;
  description?: string | null;
  external_id?: string | null;
  created_at?: string;
}

export interface RequirementCreate {
  title: string;
  description?: string | null;
  external_id?: string | null;
}

export interface RequirementUpdate {
  title?: string;
  description?: string | null;
  external_id?: string | null;
}

export interface Commit {
  id: number;
  project_id: number;
  version_id?: number | null;
  commit_sha: string;
  message?: string | null;
  author?: string | null;
  committed_at?: string | null;
}

export interface ImpactAnalysis {
  id: number;
  project_id: number;
  status: string;
  triggered_at?: string | null;
  result_summary?: string | null;
  result_store_path?: string | null;
}

export interface ImpactAnalysisCreate {
  commit_ids: number[];
}

export interface WatchStatusVersion {
  id: number;
  branch?: string | null;
  last_parsed_commit: string | null;
}

export interface WatchStatus {
  project_id: number;
  watch_enabled: boolean;
  versions: WatchStatusVersion[];
}

export function listProjects(): Promise<Project[]> {
  return request<Project[]>("/api/projects");
}

export function createProject(body: ProjectCreate): Promise<Project> {
  return request<Project>("/api/projects", { method: "POST", body });
}

export function getProject(projectId: number): Promise<Project> {
  return request<Project>(`/api/projects/${projectId}`);
}

export function updateProject(projectId: number, body: ProjectUpdate): Promise<Project> {
  return request<Project>(`/api/projects/${projectId}`, { method: "PATCH", body });
}

export function deleteProject(projectId: number): Promise<void> {
  return request<void>(`/api/projects/${projectId}`, { method: "DELETE" });
}

export function listProjectBranches(projectId: number): Promise<string[]> {
  return request<string[]>(`/api/projects/${projectId}/branches`);
}

export function listVersions(projectId: number): Promise<Version[]> {
  return request<Version[]>(`/api/projects/${projectId}/versions`);
}

export function createVersion(projectId: number, body: VersionCreate): Promise<Version> {
  return request<Version>(`/api/projects/${projectId}/versions`, { method: "POST", body });
}

export function deleteVersion(projectId: number, versionId: number): Promise<void> {
  return request<void>(`/api/projects/${projectId}/versions/${versionId}`, { method: "DELETE" });
}

export function listRequirements(projectId: number): Promise<Requirement[]> {
  return request<Requirement[]>(`/api/projects/${projectId}/requirements`);
}

export function createRequirement(
  projectId: number,
  body: RequirementCreate
): Promise<Requirement> {
  return request<Requirement>(`/api/projects/${projectId}/requirements`, {
    method: "POST",
    body,
  });
}

export function bindRequirementCommits(
  projectId: number,
  requirementId: number,
  commitIds: number[]
): Promise<void> {
  return request<void>(
    `/api/projects/${projectId}/requirements/${requirementId}/commits`,
    { method: "POST", body: { commit_ids: commitIds } }
  );
}

export function listCommits(
  projectId: number,
  params?: { version_id?: number; requirement_id?: number }
): Promise<Commit[]> {
  const search = new URLSearchParams();
  if (params?.version_id != null) search.set("version_id", String(params.version_id));
  if (params?.requirement_id != null) search.set("requirement_id", String(params.requirement_id));
  const q = search.toString();
  return request<Commit[]>(`/api/projects/${projectId}/commits${q ? `?${q}` : ""}`);
}

export interface ListCommitsByVersionParams {
  message?: string;
  committed_at_from?: string;
  committed_at_to?: string;
  id?: number;
  sha?: string;
}

export function listCommitsByVersion(
  projectId: number,
  versionId: number,
  params?: ListCommitsByVersionParams
): Promise<Commit[]> {
  const search = new URLSearchParams();
  if (params?.message != null && params.message !== "") search.set("message", params.message);
  if (params?.committed_at_from != null && params.committed_at_from !== "")
    search.set("committed_at_from", params.committed_at_from);
  if (params?.committed_at_to != null && params.committed_at_to !== "")
    search.set("committed_at_to", params.committed_at_to);
  if (params?.id != null) search.set("id", String(params.id));
  if (params?.sha != null && params.sha !== "") search.set("sha", params.sha);
  const q = search.toString();
  return request<Commit[]>(
    `/api/projects/${projectId}/versions/${versionId}/commits${q ? `?${q}` : ""}`
  );
}

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  properties?: Record<string, unknown>;
}

export function listNodesByVersion(
  projectId: number,
  versionId: number,
  params?: { name?: string; type?: string }
): Promise<GraphNode[]> {
  const search = new URLSearchParams();
  if (params?.name != null && params.name !== "") search.set("name", params.name);
  if (params?.type != null && params.type !== "") search.set("type", params.type);
  const q = search.toString();
  return request<GraphNode[]>(
    `/api/projects/${projectId}/versions/${versionId}/nodes${q ? `?${q}` : ""}`
  );
}

export function createImpactAnalysis(
  projectId: number,
  body: ImpactAnalysisCreate
): Promise<ImpactAnalysis> {
  return request<ImpactAnalysis>(`/api/projects/${projectId}/impact-analyses`, {
    method: "POST",
    body,
  });
}

export function listImpactAnalyses(projectId: number): Promise<ImpactAnalysis[]> {
  return request<ImpactAnalysis[]>(`/api/projects/${projectId}/impact-analyses`);
}

export function getImpactAnalysis(
  projectId: number,
  analysisId: number
): Promise<ImpactAnalysis> {
  return request<ImpactAnalysis>(`/api/projects/${projectId}/impact-analyses/${analysisId}`);
}

export function getWatchStatus(projectId: number): Promise<WatchStatus> {
  return request<WatchStatus>(`/api/projects/${projectId}/watch-status`);
}

// --- AI 预处理（单分支）---
export interface PreprocessLogEntry {
  at: string;
  message: string;
}

export interface PreprocessStatusItem {
  project_id: number;
  branch: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  finished_at: string | null;
  error_message?: string | null;
  extra?: { logs?: PreprocessLogEntry[]; saved?: number; skipped?: number } | null;
}

export interface PreprocessStatusResponse {
  items: PreprocessStatusItem[];
}

export interface PreprocessTriggerResponse {
  status: string;
  project_id: number;
  branch: string;
  message: string;
  extra?: Record<string, unknown>;
}

export function getPreprocessStatus(
  projectId: number,
  branch?: string | null
): Promise<PreprocessStatusItem | PreprocessStatusResponse> {
  const q = branch != null && branch !== "" ? `?branch=${encodeURIComponent(branch)}` : "";
  return request<PreprocessStatusItem | PreprocessStatusResponse>(
    `/api/projects/${projectId}/preprocess/status${q}`
  );
}

export function postPreprocess(
  projectId: number,
  branch: string = "main",
  force: boolean = false
): Promise<PreprocessTriggerResponse> {
  const params = new URLSearchParams();
  params.set("branch", branch);
  if (force) params.set("force", "true");
  return request<PreprocessTriggerResponse>(
    `/api/projects/${projectId}/preprocess?${params.toString()}`,
    { method: "POST" }
  );
}

export function syncCommits(projectId: number): Promise<SyncCommitsResponse> {
  return request<SyncCommitsResponse>(`/api/projects/${projectId}/sync-commits`, {
    method: "POST",
  });
}

export interface SyncVersionResponse {
  project_id: number;
  version_id: number;
  branch: string;
  commits_synced: number;
  graph_action: "full" | "incremental" | null;
  graph_errors?: string[];
}

export interface SyncCommitsResponse {
  project_id: number;
  versions_synced?: number;
  commits_synced?: number;
  graph_actions?: { version_id: number; branch: string; action: string }[];
  graph_errors?: string[] | null;
}

export function syncCommitsForVersion(
  projectId: number,
  versionId: number
): Promise<SyncVersionResponse> {
  return request<SyncVersionResponse>(
    `/api/projects/${projectId}/versions/${versionId}/sync-commits`,
    { method: "POST" }
  );
}

export interface ResolveResponse {
  repo_root: string;
}
export function resolveRepo(path: string) {
  return request<ResolveResponse>("/api/repos/resolve", {
    method: "POST",
    body: { path },
  });
}

export interface BranchesResponse {
  branches: string[];
  repo_root?: string | null;
}
export function listBranches(options: {
  repo_url?: string | null;
  path?: string | null;
  username?: string;
  password?: string;
}) {
  const body: {
    repo_url?: string;
    path?: string;
    username?: string;
    password?: string;
  } = {};
  if (options.repo_url) body.repo_url = options.repo_url;
  if (options.path) body.path = options.path;
  if (options.username) body.username = options.username;
  if (options.password) body.password = options.password;
  return request<BranchesResponse>("/api/repos/branches", {
    method: "POST",
    body,
  });
}

export interface EnsureResponse {
  repo_root: string;
}
export function ensureRepo(
  repo_url: string,
  target_path: string,
  options?: { branch?: string | null; username?: string; password?: string }
) {
  const body: {
    repo_url: string;
    target_path: string;
    branch?: string;
    username?: string;
    password?: string;
  } = { repo_url, target_path };
  if (options?.branch) body.branch = options.branch;
  if (options?.username) body.username = options.username;
  if (options?.password) body.password = options.password;
  return request<EnsureResponse>("/api/repos/ensure", {
    method: "POST",
    body,
  });
}

export interface ParseResponse {
  node_count: number;
  relationship_count: number;
  file_count: number;
}
export function runParse(
  repo_path: string,
  write_neo4j: boolean = true,
  branch?: string | null
) {
  const body: { repo_path: string; write_neo4j: boolean; branch?: string } = {
    repo_path,
    write_neo4j,
  };
  if (branch) body.branch = branch;
  return request<ParseResponse>("/api/parse", {
    method: "POST",
    body,
  });
}

// --- Product API ---

export interface Product {
  id: number;
  name: string;
  code?: string | null;
  description?: string | null;
  owner?: string | null;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProductCreate {
  name: string;
  code?: string | null;
  description?: string | null;
  owner?: string | null;
}

export interface ProductUpdate {
  name?: string;
  code?: string | null;
  description?: string | null;
  owner?: string | null;
  status?: string;
}

export interface ProductVersion {
  id: number;
  product_id: number;
  version_name: string;
  description?: string | null;
  status: string;
  release_date?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ProductVersionCreate {
  version_name: string;
  description?: string | null;
  status?: string;
  release_date?: string | null;
}

export interface ProductVersionUpdate {
  version_name?: string;
  description?: string | null;
  status?: string;
  release_date?: string | null;
}

export interface VersionBranch {
  id: number;
  product_version_id: number;
  project_id: number;
  branch: string;
  project_name?: string;
}

export interface ProductRequirement {
  id: number;
  product_id: number;
  parent_id: number | null;
  level: "epic" | "story" | "task";
  title: string;
  description?: string | null;
  external_id?: string | null;
  status: string;
  priority: string;
  assignee?: string | null;
  version_id?: number | null;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
}

export interface ProductRequirementCreate {
  title: string;
  level?: string;
  parent_id?: number | null;
  description?: string | null;
  external_id?: string | null;
  status?: string;
  priority?: string;
  assignee?: string | null;
  version_id: number;
  sort_order?: number;
}

export interface ProductRequirementUpdate {
  title?: string;
  level?: string;
  parent_id?: number | null;
  description?: string | null;
  external_id?: string | null;
  status?: string;
  priority?: string;
  assignee?: string | null;
  version_id?: number | null;
  sort_order?: number;
}

export interface ProductBug {
  id: number;
  product_id: number;
  title: string;
  description?: string | null;
  external_id?: string | null;
  severity: string;
  status: string;
  priority: string;
  assignee?: string | null;
  reporter?: string | null;
  version_id?: number | null;
  fix_version_id?: number | null;
  requirement_id?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface ProductBugCreate {
  title: string;
  description?: string | null;
  external_id?: string | null;
  severity?: string;
  status?: string;
  priority?: string;
  assignee?: string | null;
  reporter?: string | null;
  version_id: number;
  fix_version_id?: number | null;
  requirement_id?: number | null;
}

export interface ProductBugUpdate {
  title?: string;
  description?: string | null;
  severity?: string;
  status?: string;
  priority?: string;
  assignee?: string | null;
  reporter?: string | null;
  version_id?: number | null;
  fix_version_id?: number | null;
  requirement_id?: number | null;
}

// Product CRUD
export function listProducts(status?: string): Promise<Product[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<Product[]>(`/api/products${q}`);
}

export function createProduct(body: ProductCreate): Promise<Product> {
  return request<Product>("/api/products", { method: "POST", body });
}

export function getProduct(productId: number): Promise<Product> {
  return request<Product>(`/api/products/${productId}`);
}

export function updateProduct(productId: number, body: ProductUpdate): Promise<Product> {
  return request<Product>(`/api/products/${productId}`, { method: "PATCH", body });
}

export function deleteProduct(productId: number): Promise<void> {
  return request<void>(`/api/products/${productId}`, { method: "DELETE" });
}

// Product-Project binding
export interface ProjectCreateInProduct {
  name: string;
  repo_path: string;
  repo_username?: string | null;
  repo_password?: string | null;
}

export function createProjectInProduct(productId: number, body: ProjectCreateInProduct): Promise<Project> {
  return request<Project>(`/api/products/${productId}/projects/create`, { method: "POST", body });
}

export function listProductProjects(productId: number): Promise<Project[]> {
  return request<Project[]>(`/api/products/${productId}/projects`);
}

export function bindProductProject(productId: number, projectId: number): Promise<void> {
  return request<void>(`/api/products/${productId}/projects`, {
    method: "POST",
    body: { project_id: projectId },
  });
}

export function unbindProductProject(productId: number, projectId: number): Promise<void> {
  return request<void>(`/api/products/${productId}/projects/${projectId}`, { method: "DELETE" });
}

// Product Versions
export function listProductVersions(productId: number, status?: string): Promise<ProductVersion[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<ProductVersion[]>(`/api/products/${productId}/versions${q}`);
}

export function createProductVersion(productId: number, body: ProductVersionCreate): Promise<ProductVersion> {
  return request<ProductVersion>(`/api/products/${productId}/versions`, { method: "POST", body });
}

export function getProductVersion(productId: number, versionId: number): Promise<ProductVersion> {
  return request<ProductVersion>(`/api/products/${productId}/versions/${versionId}`);
}

export function updateProductVersion(productId: number, versionId: number, body: ProductVersionUpdate): Promise<ProductVersion> {
  return request<ProductVersion>(`/api/products/${productId}/versions/${versionId}`, { method: "PATCH", body });
}

export function deleteProductVersion(productId: number, versionId: number): Promise<void> {
  return request<void>(`/api/products/${productId}/versions/${versionId}`, { method: "DELETE" });
}

// Version branch mapping
export function listVersionBranches(productId: number, versionId: number): Promise<VersionBranch[]> {
  return request<VersionBranch[]>(`/api/products/${productId}/versions/${versionId}/branches`);
}

export function setVersionBranch(productId: number, versionId: number, projectId: number, branch: string): Promise<VersionBranch> {
  return request<VersionBranch>(`/api/products/${productId}/versions/${versionId}/branches`, {
    method: "POST",
    body: { project_id: projectId, branch },
  });
}

// Product Requirements
export function listProductRequirements(
  productId: number,
  params?: { level?: string; parent_id?: number; status?: string; version_id?: number }
): Promise<ProductRequirement[]> {
  const search = new URLSearchParams();
  if (params?.level) search.set("level", params.level);
  if (params?.parent_id != null) search.set("parent_id", String(params.parent_id));
  if (params?.status) search.set("status", params.status);
  if (params?.version_id != null) search.set("version_id", String(params.version_id));
  const q = search.toString();
  return request<ProductRequirement[]>(`/api/products/${productId}/requirements${q ? `?${q}` : ""}`);
}

export function listProductRequirementsTree(productId: number, versionId?: number): Promise<ProductRequirement[]> {
  const q = versionId != null ? `?version_id=${versionId}` : "";
  return request<ProductRequirement[]>(`/api/products/${productId}/requirements/tree${q}`);
}

export function createProductRequirement(productId: number, body: ProductRequirementCreate): Promise<ProductRequirement> {
  return request<ProductRequirement>(`/api/products/${productId}/requirements`, { method: "POST", body });
}

export function updateProductRequirement(productId: number, reqId: number, body: ProductRequirementUpdate): Promise<ProductRequirement> {
  return request<ProductRequirement>(`/api/products/${productId}/requirements/${reqId}`, { method: "PATCH", body });
}

export function deleteProductRequirement(productId: number, reqId: number): Promise<void> {
  return request<void>(`/api/products/${productId}/requirements/${reqId}`, { method: "DELETE" });
}

export function listRequirementCommits(productId: number, reqId: number): Promise<Commit[]> {
  return request<Commit[]>(`/api/products/${productId}/requirements/${reqId}/commits`);
}

export function bindRequirementCommitsProduct(productId: number, reqId: number, commitIds: number[]): Promise<void> {
  return request<void>(`/api/products/${productId}/requirements/${reqId}/commits`, {
    method: "POST",
    body: { commit_ids: commitIds },
  });
}

// Product Bugs
export function listProductBugs(
  productId: number,
  params?: { status?: string; severity?: string; version_id?: number }
): Promise<ProductBug[]> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.severity) search.set("severity", params.severity);
  if (params?.version_id != null) search.set("version_id", String(params.version_id));
  const q = search.toString();
  return request<ProductBug[]>(`/api/products/${productId}/bugs${q ? `?${q}` : ""}`);
}

export function createProductBug(productId: number, body: ProductBugCreate): Promise<ProductBug> {
  return request<ProductBug>(`/api/products/${productId}/bugs`, { method: "POST", body });
}

export function updateProductBug(productId: number, bugId: number, body: ProductBugUpdate): Promise<ProductBug> {
  return request<ProductBug>(`/api/products/${productId}/bugs/${bugId}`, { method: "PATCH", body });
}

export function deleteProductBug(productId: number, bugId: number): Promise<void> {
  return request<void>(`/api/products/${productId}/bugs/${bugId}`, { method: "DELETE" });
}

export function listBugCommits(productId: number, bugId: number): Promise<Commit[]> {
  return request<Commit[]>(`/api/products/${productId}/bugs/${bugId}/commits`);
}

export function bindBugCommits(productId: number, bugId: number, commitIds: number[]): Promise<void> {
  return request<void>(`/api/products/${productId}/bugs/${bugId}/commits`, {
    method: "POST",
    body: { commit_ids: commitIds },
  });
}

// --- AI Agent API ---

export interface AgentMessage {
  id?: number;
  conversation_id?: number;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  tool_calls?: unknown[] | null;
  tool_call_id?: string | null;
  token_in?: number | null;
  token_out?: number | null;
  latency_ms?: number | null;
  model?: string | null;
  created_at?: string;
}

export interface AgentConversation {
  conversation_id: number;
  thread_id: string;
  agent_profile: string;
  route_context_key: string;
  product_id?: number | null;
}

export interface SSEEvent {
  event: "token" | "tool_start" | "tool_end" | "done" | "error";
  data: unknown;
}

export function resolveAgentSession(
  sessionId: string,
  routeContextKey: string,
  projectId?: number | null,
  productId?: number | null,
): Promise<AgentConversation> {
  return request<AgentConversation>("/api/agent/sessions/resolve", {
    method: "POST",
    body: {
      session_id: sessionId,
      route_context_key: routeContextKey,
      project_id: projectId ?? undefined,
      product_id: productId ?? undefined,
    },
  });
}

export function getAgentMessages(
  conversationId: number,
  limit: number = 50,
  offset: number = 0
): Promise<{ messages: AgentMessage[]; conversation_id: number }> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return request<{ messages: AgentMessage[]; conversation_id: number }>(
    `/api/agent/conversations/${conversationId}/messages?${params.toString()}`
  );
}

export function sendAgentMessage(
  conversationId: number,
  message: string
): Promise<{ role: string; content: string; message_id: number }> {
  return request<{ role: string; content: string; message_id: number }>(
    "/api/agent/chat",
    {
      method: "POST",
      body: { conversation_id: conversationId, message, stream: false },
    }
  );
}

/**
 * SSE 流式 Agent 对话。通过回调逐步推送事件。
 * 返回 AbortController 用于取消。
 */
export function streamAgentChat(
  conversationId: number,
  message: string,
  callbacks: {
    onToken?: (text: string) => void;
    onToolEvent?: (event: SSEEvent) => void;
    onDone?: (data: { content: string; token_in?: number; token_out?: number }) => void;
    onError?: (error: string) => void;
  }
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          message,
          stream: true,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        callbacks.onError?.((data as { detail?: string }).detail ?? res.statusText);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError?.("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event: SSEEvent = JSON.parse(jsonStr);

            switch (event.event) {
              case "token":
                callbacks.onToken?.(event.data as string);
                break;
              case "tool_start":
              case "tool_end":
                callbacks.onToolEvent?.(event);
                break;
              case "done":
                callbacks.onDone?.(
                  event.data as { content: string; token_in?: number; token_out?: number }
                );
                break;
              case "error":
                callbacks.onError?.((event.data as { message: string }).message);
                break;
            }
          } catch {
            // 忽略无法解析的行
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        callbacks.onError?.((err as Error).message);
      }
    }
  })();

  return controller;
}
