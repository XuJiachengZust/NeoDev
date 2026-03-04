import { http, HttpResponse } from "msw";

const API_BASE = "/api";

export const projectFixture = {
  id: 1,
  name: "P1",
  repo_path: "/path/to/repo",
  created_at: "2024-01-01T00:00:00Z",
  watch_enabled: false,
  neo4j_database: null,
  neo4j_identifier: null,
};

export const versionFixture = {
  id: 1,
  project_id: 1,
  branch: "main",
  version_name: "main",
  created_at: "2024-01-01T00:00:00Z",
  last_parsed_commit: null,
};

export const requirementFixture = {
  id: 1,
  project_id: 1,
  title: "R1",
  description: null,
  external_id: null,
  created_at: "2024-01-01T00:00:00Z",
};

export const commitFixture = {
  id: 1,
  project_id: 1,
  version_id: 1,
  commit_sha: "abc123",
  message: "feat: init",
  author: "dev",
  committed_at: "2024-01-01T00:00:00Z",
};

export const impactAnalysisFixture = {
  id: 1,
  project_id: 1,
  status: "pending",
  triggered_at: "2024-01-01T00:00:00Z",
  result_summary: null,
};

export const watchStatusFixture = {
  project_id: 1,
  watch_enabled: false,
  versions: [
    { id: 1, branch: "main", last_parsed_commit: null },
  ],
};

export const handlers = [
  http.get(`${API_BASE}/projects`, () => {
    return HttpResponse.json([projectFixture]);
  }),
  http.post(`${API_BASE}/projects`, async ({ request }) => {
    const body = (await request.json()) as { name: string; repo_path: string };
    return HttpResponse.json(
      { id: 2, ...body, created_at: "2024-01-01T00:00:00Z", watch_enabled: false, neo4j_database: null, neo4j_identifier: null },
      { status: 201 }
    );
  }),
  http.get(`${API_BASE}/projects/:project_id`, ({ params }) => {
    const id = Number(params.project_id);
    if (id === 1) return HttpResponse.json(projectFixture);
    return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
  }),
  http.patch(`${API_BASE}/projects/:project_id`, async ({ request, params }) => {
    const id = Number(params.project_id);
    if (id !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...projectFixture, ...body });
  }),
  http.delete(`${API_BASE}/projects/:project_id`, ({ params }) => {
    const id = Number(params.project_id);
    if (id !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${API_BASE}/projects/:project_id/versions`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return HttpResponse.json([versionFixture]);
  }),
  http.post(`${API_BASE}/projects/:project_id/versions`, async ({ request, params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    const body = (await request.json()) as { branch?: string; version_name?: string };
    return HttpResponse.json(
      { id: 2, project_id: 1, ...body, created_at: "2024-01-01T00:00:00Z", last_parsed_commit: null },
      { status: 201 }
    );
  }),
  http.delete(`${API_BASE}/projects/:project_id/versions/:version_id`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Version or project not found" }, { status: 404 });
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${API_BASE}/projects/:project_id/requirements`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return HttpResponse.json([requirementFixture]);
  }),

  http.get(`${API_BASE}/projects/:project_id/commits`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return HttpResponse.json([commitFixture, { ...commitFixture, id: 2, commit_sha: "def456" }]);
  }),
  http.get(`${API_BASE}/projects/:project_id/versions/:version_id/commits`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project or version not found" }, { status: 404 });
    return HttpResponse.json([commitFixture]);
  }),

  http.post(`${API_BASE}/projects/:project_id/impact-analyses`, async ({ request, params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    const body = (await request.json()) as { commit_ids: number[] };
    if (!body.commit_ids?.length) return HttpResponse.json({ detail: "commit_ids must not be empty" }, { status: 400 });
    return HttpResponse.json(
      { id: 1, project_id: 1, status: "pending", triggered_at: new Date().toISOString(), result_summary: null },
      { status: 201 }
    );
  }),
  http.get(`${API_BASE}/projects/:project_id/impact-analyses`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return HttpResponse.json([impactAnalysisFixture]);
  }),
  http.get(`${API_BASE}/projects/:project_id/impact-analyses/:analysis_id`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Impact analysis not found" }, { status: 404 });
    return HttpResponse.json(impactAnalysisFixture);
  }),

  http.get(`${API_BASE}/projects/:project_id/watch-status`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return HttpResponse.json(watchStatusFixture);
  }),
  http.post(`${API_BASE}/projects/:project_id/sync-commits`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return HttpResponse.json({ synced: true });
  }),

  http.post("/api/repos/branches", async () => {
    return HttpResponse.json({ branches: ["main", "develop"], repo_root: "/path/to/repo" });
  }),

  http.post(`${API_BASE}/projects/:project_id/requirements/:requirement_id/commits`, ({ params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    return new HttpResponse(null, { status: 204 });
  }),
  http.post(`${API_BASE}/projects/:project_id/requirements`, async ({ request, params }) => {
    if (Number(params.project_id) !== 1) return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
    const body = (await request.json()) as { title: string };
    return HttpResponse.json(
      { id: 2, project_id: 1, title: body.title ?? "", description: null, external_id: null, created_at: "2024-01-01T00:00:00Z" },
      { status: 201 }
    );
  }),
];
