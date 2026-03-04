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
}

export interface ProjectCreate {
  name: string;
  repo_path: string;
  watch_enabled?: boolean;
  neo4j_database?: string | null;
  neo4j_identifier?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  repo_path?: string;
  watch_enabled?: boolean;
  neo4j_database?: string | null;
  neo4j_identifier?: string | null;
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

export function listCommitsByVersion(projectId: number, versionId: number): Promise<Commit[]> {
  return request<Commit[]>(`/api/projects/${projectId}/versions/${versionId}/commits`);
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

export function syncCommits(projectId: number): Promise<{ synced?: boolean }> {
  return request<{ synced?: boolean }>(`/api/projects/${projectId}/sync-commits`, {
    method: "POST",
  });
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
