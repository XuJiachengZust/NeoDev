import { RepoResolve } from "../components/RepoResolve";
import { ParseTask } from "../components/ParseTask";

export function RepoParsePage() {
  return (
    <div data-testid="page-repos">
      <h2>仓库解析管理</h2>
      <RepoResolve />
      <ParseTask />
    </div>
  );
}
