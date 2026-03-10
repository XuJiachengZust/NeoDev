import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useAgentSession } from "../contexts/AgentSessionContext";
import { useRouteContextKey } from "../hooks/useRouteContextKey";
import { useProductContext } from "../hooks/useProductContext";
import { AgentQuickCommands } from "./AgentQuickCommands";
import type { AgentMessage } from "../api/client";

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
    resolve,
    send,
    cancel,
    routeContextKey,
    productId: sessionProductId,
  } = useAgentSession();

  const { routeContextKey: currentRouteKey, projectId } = useRouteContextKey();
  const { productId: routeProductId, routeHint } = useProductContext();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 路由变化时自动 resolve（支持产品模式）
  useEffect(() => {
    if (routeProductId) {
      // 产品模式
      resolve(routeHint, null, routeProductId);
    } else {
      // 旧模式
      resolve(currentRouteKey, projectId);
    }
  }, [currentRouteKey, projectId, routeProductId, routeHint, resolve]);

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
          {/* 顶部：上下文标签 */}
          <div className="agent-chat-header">
            <span className="agent-chat-title">NeoDev Agent</span>
            <span className="agent-context-badge">{contextLabel}</span>
            {streaming && <span className="agent-status-dot streaming" />}
          </div>

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
              <MessageBubble key={msg.id ?? `msg-${i}`} message={msg} />
            ))}
            {error && (
              <div className="agent-chat-error">{error}</div>
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

function MessageBubble({ message }: { message: AgentMessage }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  const [toolExpanded, setToolExpanded] = useState(false);

  if (isTool) {
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
