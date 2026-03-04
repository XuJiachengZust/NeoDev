import { beforeAll, afterEach, afterAll, describe, it, expect } from "vitest";
import { setupServer } from "msw/node";
import { handlers } from "../test/mocks/handlers";
import {
  listProjects,
  createProject,
  getProject,
  updateProject,
  deleteProject,
  listVersions,
  createVersion,
  deleteVersion,
  listRequirements,
  listCommits,
  listCommitsByVersion,
  createImpactAnalysis,
  listImpactAnalyses,
  getImpactAnalysis,
  getWatchStatus,
  syncCommits,
} from "./client";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("impact API client", () => {
  describe("projects", () => {
    it("listProjects returns Project[]", async () => {
      const list = await listProjects();
      expect(list).toHaveLength(1);
      expect(list[0]).toMatchObject({ id: 1, name: "P1", repo_path: "/path/to/repo" });
    });

    it("createProject POSTs body and returns Project", async () => {
      const created = await createProject({
        name: "P2",
        repo_path: "/other",
      });
      expect(created).toMatchObject({ name: "P2", repo_path: "/other" });
      expect(created.id).toBeDefined();
    });

    it("getProject returns project by id", async () => {
      const p = await getProject(1);
      expect(p).toMatchObject({ id: 1, name: "P1" });
    });

    it("getProject throws on 404", async () => {
      await expect(getProject(999)).rejects.toThrow();
    });

    it("updateProject PATCHes and returns updated project", async () => {
      const updated = await updateProject(1, { name: "P1-renamed" });
      expect(updated).toMatchObject({ name: "P1-renamed" });
    });

    it("deleteProject returns void on 204", async () => {
      await expect(deleteProject(1)).resolves.toBeUndefined();
    });
  });

  describe("versions", () => {
    it("listVersions returns Version[]", async () => {
      const list = await listVersions(1);
      expect(list).toHaveLength(1);
      expect(list[0]).toMatchObject({ id: 1, branch: "main", project_id: 1 });
    });

    it("createVersion POSTs body and returns Version", async () => {
      const created = await createVersion(1, { branch: "develop", version_name: "dev" });
      expect(created).toMatchObject({ branch: "develop", project_id: 1 });
      expect(created.id).toBeDefined();
    });

    it("deleteVersion returns void on 204", async () => {
      await expect(deleteVersion(1, 1)).resolves.toBeUndefined();
    });
  });

  describe("requirements", () => {
    it("listRequirements returns Requirement[]", async () => {
      const list = await listRequirements(1);
      expect(list).toHaveLength(1);
      expect(list[0]).toMatchObject({ id: 1, title: "R1", project_id: 1 });
    });
  });

  describe("commits", () => {
    it("listCommits returns Commit[]", async () => {
      const list = await listCommits(1);
      expect(list.length).toBeGreaterThanOrEqual(1);
      expect(list[0]).toMatchObject({ commit_sha: "abc123", project_id: 1 });
    });

    it("listCommitsByVersion returns Commit[]", async () => {
      const list = await listCommitsByVersion(1, 1);
      expect(list).toHaveLength(1);
      expect(list[0]).toMatchObject({ commit_sha: "abc123" });
    });
  });

  describe("impact analyses", () => {
    it("createImpactAnalysis POSTs commit_ids and returns ImpactAnalysis", async () => {
      const created = await createImpactAnalysis(1, { commit_ids: [1, 2] });
      expect(created).toMatchObject({ project_id: 1, status: "pending" });
      expect(created.id).toBeDefined();
    });

    it("createImpactAnalysis throws on empty commit_ids", async () => {
      await expect(createImpactAnalysis(1, { commit_ids: [] })).rejects.toThrow();
    });

    it("listImpactAnalyses returns ImpactAnalysis[]", async () => {
      const list = await listImpactAnalyses(1);
      expect(list).toHaveLength(1);
      expect(list[0]).toMatchObject({ id: 1, status: "pending" });
    });

    it("getImpactAnalysis returns single analysis", async () => {
      const a = await getImpactAnalysis(1, 1);
      expect(a).toMatchObject({ id: 1, project_id: 1, status: "pending" });
    });
  });

  describe("sync and watch", () => {
    it("getWatchStatus returns WatchStatus", async () => {
      const status = await getWatchStatus(1);
      expect(status).toMatchObject({ project_id: 1, watch_enabled: false });
      expect(status.versions).toHaveLength(1);
      expect(status.versions[0]).toMatchObject({ branch: "main" });
    });

    it("syncCommits returns summary", async () => {
      const result = await syncCommits(1);
      expect(result).toMatchObject({ synced: true });
    });
  });
});
