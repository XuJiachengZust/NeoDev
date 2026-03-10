interface QuickCommand {
  label: string;
  message: string;
}

const PRODUCT_COMMANDS: QuickCommand[] = [
  { label: "产品概览", message: "请给我这个产品的整体概览，包括版本、需求和 Bug 状态。" },
  { label: "需求分析", message: "分析当前产品的需求完成度，哪些 Epic 还有未完成的 Story？" },
  { label: "Bug 趋势", message: "分析当前产品的 Bug 分布情况，有哪些高优先级 Bug 需要关注？" },
  { label: "版本进度", message: "当前开发中的版本进度如何？各项目分支的提交情况怎样？" },
];

interface AgentQuickCommandsProps {
  onSelect: (message: string) => void;
  disabled?: boolean;
}

export function AgentQuickCommands({ onSelect, disabled }: AgentQuickCommandsProps) {
  return (
    <div className="agent-quick-commands">
      {PRODUCT_COMMANDS.map((cmd) => (
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
