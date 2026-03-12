import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useAgentSession } from "../contexts/AgentSessionContext";
import { useRouteContextKey } from "../hooks/useRouteContextKey";
import { useProductContext } from "../hooks/useProductContext";
import { AgentQuickCommands } from "./AgentQuickCommands";
import type { AgentMessage, SubagentStep } from "../api/client";

interface AgentPanelProps {
  collapsed: boolean;
  onToggle: () => void;
}

const CONTEXT_LABELS: Record<string, string> = {
  default: "通用助手",
  onboard: "项目接入",
  graph_build: "图谱构建",
  cockpit_requirements: "需求分析",
  cockpit_impact: "影响分析",
  product: "产品助手",
  product_dashboard: "产品概览",
  product_projects: "产品项目",
  product_versions: "产品版本",
  product_requirements: "版本需求",
  product_bugs: "版本Bug",
};

export function AgentPanel({ collapsed, onToggle }: AgentPanelProps) {
  const {
    messages,
    streaming,
    resolving,
    error,
    recursionLimitHit,
    resolve,
    send,
    cancel,
    continueGeneration,
    routeContextKey,
    productId: sessionProductId,
    versionName,
    productName,
    projectBranches,
    conversations,
    currentConversationId,
    createNewConversation,
    switchConversation,
  } = useAgentSession();

  const { routeContextKey: currentRouteKey, projectId } = useRouteContextKey();
  const { productId: routeProductId, versionId: routeVersionId, routeHint } = useProductContext();
  const [input, setInput] = useState("");
  const [ctxExpanded, setCtxExpanded] = useState(false);
  const [convListOpen, setConvListOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 路由变化时自动 resolve（支持产品模式 + 版本）
  useEffect(() => {
    if (routeProductId) {
      resolve(routeHint, null, routeProductId, routeVersionId);
    } else {
      resolve(currentRouteKey, projectId);
    }
  }, [currentRouteKey, projectId, routeProductId, routeVersionId, routeHint, resolve]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    send(text);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const contextLabel = CONTEXT_LABELS[routeContextKey ?? "default"] ?? "通用助手";
  const isProductMode = !!sessionProductId;

  return (
    <div
      className={`app-agent-wrap ${collapsed ? "collapsed" : ""}`}
      data-testid="agent-panel"
    >
      <button
        type="button"
        className="app-agent-toggle"
        onClick={onToggle}
        aria-label={collapsed ? "展开 Agent" : "收起 Agent"}
        data-testid="agent-toggle"
      >
        {collapsed ? "◀" : "▶"}
      </button>
      {!collapsed && (
        <div className="agent-chat-panel">
          {/* 顶部：上下文标签 + 对话管理 */}
          <div className="agent-chat-header">
            <span className="agent-chat-title">NeoDev Agent</span>
            <span className="agent-context-badge">{contextLabel}</span>
            {streaming && <span className="agent-status-dot streaming" />}
            {isProductMode && (
              <div className="agent-header-actions">
                <button
                  type="button"
                  className="agent-conv-list-btn"
                  onClick={() => setConvListOpen(!convListOpen)}
                  title="对话列表"
                >
                  ☰
                </button>
                <button
                  type="button"
                  className="agent-new-conv-btn"
                  onClick={() => { createNewConversation(); setConvListOpen(false); }}
                  title="新建对话"
                >
                  +
                </button>
              </div>
            )}
          </div>

          {/* 对话列表下拉 */}
          {convListOpen && isProductMode && (
            <div className="agent-conv-list">
              {conversations.length === 0 && (
                <div className="agent-conv-list-empty">暂无历史对话</div>
              )}
              {conversations.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`agent-conv-item ${c.id === currentConversationId ? "active" : ""}`}
                  onClick={() => { switchConversation(c.id); setConvListOpen(false); }}
                >
                  <span className="agent-conv-title">
                    {c.title || "新对话"}
                  </span>
                  <span className="agent-conv-meta">
                    {c.message_count} 条 · {new Date(c.created_at).toLocaleDateString()}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* 上下文信息面板（仅产品模式） */}
          {isProductMode && (
            <div className="agent-ctx-panel">
              <button
                type="button"
                className="agent-ctx-toggle"
                onClick={() => setCtxExpanded(!ctxExpanded)}
              >
                {ctxExpanded ? "▾" : "▸"} {productName ?? "产品"}
                {versionName ? ` · ${versionName}` : " · 未选择版本"}
              </button>
              {ctxExpanded && projectBranches && projectBranches.length > 0 && (
                <div className="agent-ctx-branches">
                  {projectBranches.map((b) => (
                    <div key={b.project_id} className="agent-ctx-branch-item">
                      <span className="agent-ctx-proj-name">{b.project_name}</span>
                      <span className="agent-ctx-branch-arrow">&rarr;</span>
                      <span className="agent-ctx-branch-name">{b.branch}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 消息区域 */}
          <div className="agent-chat-messages">
            {resolving && (
              <div className="agent-chat-skeleton">
                <div className="skeleton-line" />
                <div className="skeleton-line short" />
              </div>
            )}
            {!resolving && messages.length === 0 && (
              <div className="agent-chat-empty">
                有什么我可以帮助你的？
                {sessionProductId && (
                  <div style={{ marginTop: 16 }}>
                    <AgentQuickCommands onSelect={send} disabled={streaming} />
                  </div>
                )}
              </div>
            )}
            {messages.map((msg, i) => (
              <MessageBubble key={msg.id ?? `msg-${i}`} message={msg} streaming={streaming} />
            ))}
            {error && (
              <div className="agent-chat-error">{error}</div>
            )}
            {recursionLimitHit && (
              <div className="agent-chat-warning">
                <div className="agent-chat-warning-text">
                  我已经进行了很多轮思考，到达了循环上限。你可以选择让我继续。
                </div>
                <button
                  type="button"
                  className="agent-chat-warning-btn"
                  onClick={continueGeneration}
                  disabled={streaming}
                >
                  继续
                </button>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="agent-chat-input-wrap">
            <textarea
              ref={inputRef}
              className="agent-chat-input"
              placeholder="输入消息..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={resolving}
              rows={1}
            />
            {streaming ? (
              <button
                type="button"
                className="agent-chat-btn stop"
                onClick={cancel}
                title="停止生成"
              >
                ■
              </button>
            ) : (
              <button
                type="button"
                className="agent-chat-btn send"
                onClick={handleSend}
                disabled={!input.trim() || resolving}
                title="发送"
              >
                ▶
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message, streaming }: { message: AgentMessage; streaming: boolean }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  const [toolExpanded, setToolExpanded] = useState(false);

  const isTaskTool = isTool && message.content.startsWith("[调用工具] task");
  const hasSubagent = isTaskTool && (!!message.subagent_content || (message.subagent_steps && message.subagent_steps.length > 0));

  // 子智能体：流式过程中默认展开，结束后自动折叠
  const isSubagentStreaming = hasSubagent && streaming;
  const [subagentExpanded, setSubagentExpanded] = useState(false);
  const prevStreamingRef = useRef(streaming);

  useEffect(() => {
    if (hasSubagent) {
      // 流式开始时展开
      if (streaming && !prevStreamingRef.current) {
        setSubagentExpanded(true);
      }
      // 流式结束时折叠
      if (!streaming && prevStreamingRef.current) {
        setSubagentExpanded(false);
      }
    }
    prevStreamingRef.current = streaming;
  }, [streaming, hasSubagent]);

  // 流式过程中如果有新的子智能体内容，自动展开
  useEffect(() => {
    if (isSubagentStreaming) {
      setSubagentExpanded(true);
    }
  }, [isSubagentStreaming]);

  if (isTool) {
    // 子智能体 task 工具调用
    if (isTaskTool && hasSubagent) {
      const toolCalls = message.tool_calls as Array<{ name: string; args: Record<string, unknown> }> | undefined;
      const subagentType = toolCalls?.[0]?.args?.subagent_type as string | undefined;
      const subagentLabel = subagentType ?? "task";

      return (
        <div className="agent-subagent-block">
          <button
            type="button"
            className="agent-subagent-header"
            onClick={() => setSubagentExpanded(!subagentExpanded)}
          >
            <span className="agent-subagent-arrow">{subagentExpanded ? "▾" : "▸"}</span>
            <span className="agent-subagent-label">[子智能体] {subagentLabel}</span>
            {isSubagentStreaming && <span className="agent-status-dot streaming" />}
          </button>
          {subagentExpanded && (
            <div className="agent-subagent-body">
              {message.subagent_steps && message.subagent_steps.length > 0 && (
                <div className="agent-subagent-steps">
                  {message.subagent_steps.map((step: SubagentStep, i: number) => (
                    <div key={i} className="agent-subagent-step">
                      {step.type === "tool_start" ? "▸" : "✓"} {step.name}
                      {step.type === "tool_end" && step.result && (
                        <span className="agent-subagent-step-result">
                          {" → "}{step.result.length > 80 ? step.result.slice(0, 80) + "…" : step.result}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {message.subagent_content && (
                <div className="agent-subagent-content">
                  {message.subagent_content}
                </div>
              )}
            </div>
          )}
        </div>
      );
    }

    // 普通工具调用
    return (
      <div className="agent-msg-tool">
        <button
          type="button"
          className="agent-tool-toggle"
          onClick={() => setToolExpanded(!toolExpanded)}
        >
          {toolExpanded ? "▾" : "▸"} {message.content}
        </button>
        {toolExpanded && message.tool_calls && (
          <pre className="agent-tool-detail">
            {JSON.stringify(message.tool_calls, null, 2)}
          </pre>
        )}
      </div>
    );
  }

  return (
    <div className={`agent-msg ${isUser ? "user" : "assistant"}`}>
      <div className="agent-msg-content">{message.content}</div>
      {!isUser && message.token_in != null && (
        <div className="agent-msg-meta">
          {message.token_in}↓ {message.token_out}↑
          {message.latency_ms != null && ` · ${message.latency_ms}ms`}
        </div>
      )}
    </div>
  );
}
