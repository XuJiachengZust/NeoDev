interface AgentActionCardProps {
  title: string;
  description: string;
  actions?: { label: string; onClick: () => void }[];
}

export function AgentActionCard({ title, description, actions }: AgentActionCardProps) {
  return (
    <div className="agent-action-card">
      <div className="agent-action-card-title">{title}</div>
      <div className="agent-action-card-desc">{description}</div>
      {actions && actions.length > 0 && (
        <div className="agent-action-card-actions">
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              className="agent-action-card-btn"
              onClick={a.onClick}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
