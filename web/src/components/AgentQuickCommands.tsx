interface QuickCommand {
  label: string;
  message: string;
}

const DEFAULT_PRODUCT_COMMANDS: QuickCommand[] = [
  { label: "产品概览", message: "请给我这个产品的整体概览，包括版本、需求和 Bug 状态。" },
  { label: "需求分析", message: "分析当前产品的需求完成度，哪些 Epic 还有未完成的 Story？" },
  { label: "Bug 趋势", message: "分析当前产品的 Bug 分布情况，有哪些高优先级 Bug 需要关注？" },
  { label: "版本进度", message: "当前开发中的版本进度如何？各项目分支的提交情况怎么样？" },
];

const DOC_EDITOR_COMMANDS: QuickCommand[] = [
  { label: "生成 PRD 大纲", message: "请基于当前需求上下文，生成一份标准 PRD 大纲，包含背景、目标、范围、功能点、流程、验收标准和风险。" },
  { label: "润色当前文档", message: "请润色当前需求文档，优化表达、结构和专业度，保持 Markdown 结构清晰。" },
  { label: "检查逻辑遗漏", message: "请检查当前需求文档是否存在逻辑遗漏、边界不清、依赖缺失或验收口径不完整的问题，并直接给出补充建议。" },
  { label: "提取验收标准", message: "请从当前需求文档中提取并整理验收标准（AC），输出为清晰的 Markdown 列表。" },
];

interface AgentQuickCommandsProps {
  onSelect: (message: string) => void;
  routeContextKey?: string | null;
  disabled?: boolean;
}

export function AgentQuickCommands({ onSelect, routeContextKey, disabled }: AgentQuickCommandsProps) {
  const commands = routeContextKey === "product_requirement_doc"
    ? DOC_EDITOR_COMMANDS
    : DEFAULT_PRODUCT_COMMANDS;

  return (
    <div className="agent-quick-commands">
      {commands.map((cmd) => (
        <button
          key={cmd.label}
          type="button"
          className="agent-quick-cmd"
          onClick={() => onSelect(cmd.message)}
          disabled={disabled}
        >
          {cmd.label}
        </button>
      ))}
    </div>
  );
}
