import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  resolveAgentSession,
  getAgentMessages,
  streamAgentChat,
  listAgentConversations,
  createAgentConversation,
  activateAgentConversation,
  type AgentMessage,
  type ConversationSummary,
  type SubagentStep,
  type SSEEvent,
} from "../api/client";

function findLastIndex<T>(arr: T[], predicate: (item: T) => boolean): number {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (predicate(arr[i])) return i;
  }
  return -1;
}

function generateSessionId(): string {
  const cryptoObj = globalThis.crypto;
  if (cryptoObj?.randomUUID) {
    return cryptoObj.randomUUID();
  }

  // randomUUID 在非安全上下文（如局域网 http）可能不可用，使用 getRandomValues 兜底
  if (cryptoObj?.getRandomValues) {
    const bytes = new Uint8Array(16);
    cryptoObj.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0"));
    return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10, 16).join("")}`;
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getOrCreateSessionId(): string {
  const KEY = "neodev_agent_session_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = generateSessionId();
    localStorage.setItem(KEY, id);
  }
  return id;
}

interface AgentSessionState {
  sessionId: string;
  currentConversationId: number | null;
  agentProfile: string | null;
  routeContextKey: string | null;
  productId: number | null;
  versionId: number | null;
  versionName: string | null;
  productName: string | null;
  projectBranches: Array<{ project_id: number; project_name: string; branch: string }> | null;
  conversations: ConversationSummary[];
  messages: AgentMessage[];
  streaming: boolean;
  resolving: boolean;
  error: string | null;
  recursionLimitHit: boolean;
  resolve: (
    routeContextKey: string,
    projectId?: number | null,
    productId?: number | null,
    versionId?: number | null,
  ) => Promise<void>;
  send: (message: string) => void;
  loadHistory: () => Promise<void>;
  cancel: () => void;
  continueGeneration: () => void;
  createNewConversation: () => Promise<void>;
  switchConversation: (conversationId: number) => Promise<void>;
  loadConversations: () => Promise<void>;
}

const AgentSessionContext = createContext<AgentSessionState | null>(null);

export function AgentSessionProvider({ children }: { children: ReactNode }) {
  const sessionId = useMemo(() => getOrCreateSessionId(), []);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [agentProfile, setAgentProfile] = useState<string | null>(null);
  const [routeContextKey, setRouteContextKey] = useState<string | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [versionId, setVersionId] = useState<number | null>(null);
  const [versionName, setVersionName] = useState<string | null>(null);
  const [productName, setProductName] = useState<string | null>(null);
  const [projectBranches, setProjectBranches] = useState<
    Array<{ project_id: number; project_name: string; branch: string }> | null
  >(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recursionLimitHit, setRecursionLimitHit] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const resolve = useCallback(
    async (
      ctxKey: string,
      projectId?: number | null,
      prdId?: number | null,
      verId?: number | null,
    ) => {
      const samePrd = (prdId ?? null) === productId;
      const sameVer = (verId ?? null) === versionId;

      // 产品模式：同 productId 时，如果 conversationId 已有，
      // 只要 versionId 或 routeContextKey 变化就更新上下文（不重载消息）
      if (prdId && samePrd && conversationId != null) {
        if (ctxKey !== routeContextKey || !sameVer) {
          // 后端更新上下文字段
          try {
            const conv = await resolveAgentSession(sessionId, ctxKey, projectId, prdId, verId);
            setRouteContextKey(conv.route_context_key);
            setVersionId(conv.version_id ?? null);
            setVersionName(conv.version_name ?? null);
            setProductName(conv.product_name ?? null);
            setProjectBranches(conv.project_branches ?? null);
            // 如果返回了不同的 conversationId，需要加载消息
            if (conv.conversation_id !== conversationId) {
              setConversationId(conv.conversation_id);
              const { messages: history } = await getAgentMessages(conv.conversation_id);
              setMessages(history);
            }
          } catch (err) {
            setError((err as Error).message);
          }
        }
        return;
      }

      // 非产品模式或首次 resolve
      if (ctxKey === routeContextKey && conversationId != null && samePrd) return;

      setResolving(true);
      setError(null);
      try {
        const conv = await resolveAgentSession(sessionId, ctxKey, projectId, prdId, verId);
        setConversationId(conv.conversation_id);
        setAgentProfile(conv.agent_profile);
        setRouteContextKey(conv.route_context_key);
        setProductId(conv.product_id ?? null);
        setVersionId(conv.version_id ?? null);
        setVersionName(conv.version_name ?? null);
        setProductName(conv.product_name ?? null);
        setProjectBranches(conv.project_branches ?? null);
        // 加载历史消息
        const { messages: history } = await getAgentMessages(conv.conversation_id);
        setMessages(history);
        // 产品模式加载对话列表
        if (conv.product_id) {
          const { conversations: list } = await listAgentConversations(sessionId, conv.product_id);
          setConversations(list);
        } else {
          setConversations([]);
        }
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setResolving(false);
      }
    },
    [sessionId, routeContextKey, conversationId, productId, versionId]
  );

  const loadHistory = useCallback(async () => {
    if (conversationId == null) return;
    try {
      const { messages: history } = await getAgentMessages(conversationId);
      setMessages(history);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [conversationId]);

  const loadConversations = useCallback(async () => {
    if (!productId) return;
    try {
      const { conversations: list } = await listAgentConversations(sessionId, productId);
      setConversations(list);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [sessionId, productId]);

  const createNewConversation = useCallback(async () => {
    if (!productId) return;
    setError(null);
    try {
      const conv = await createAgentConversation(
        sessionId, productId, routeContextKey ?? "product_dashboard", versionId,
      );
      const newId = (conv as { id: number }).id;
      setConversationId(newId);
      setMessages([]);
      // 刷新对话列表
      const { conversations: list } = await listAgentConversations(sessionId, productId);
      setConversations(list);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [sessionId, productId, routeContextKey, versionId]);

  const switchConversation = useCallback(async (targetId: number) => {
    if (targetId === conversationId) return;
    setError(null);
    try {
      await activateAgentConversation(targetId, sessionId);
      setConversationId(targetId);
      const { messages: history } = await getAgentMessages(targetId);
      setMessages(history);
      // 刷新对话列表
      if (productId) {
        const { conversations: list } = await listAgentConversations(sessionId, productId);
        setConversations(list);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }, [sessionId, conversationId, productId]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
  }, []);

  const continueGeneration = useCallback(() => {
    setRecursionLimitHit(false);
    // 使用 setTimeout 确保状态更新后再发送
    setTimeout(() => {
      if (conversationId == null) return;

      setStreaming(true);
      setError(null);

      let partialContent = "";

      const controller = streamAgentChat(conversationId, "请继续", {
        onToken: (text) => {
          partialContent += text;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant" && last?.id == null) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: partialContent },
              ];
            }
            return [
              ...prev,
              { role: "assistant", content: partialContent } as AgentMessage,
            ];
          });
        },
        onToolEvent: (event) => {
          if (event.event === "tool_start") {
            const data = event.data as { name: string; args: unknown };
            setMessages((prev) => [
              ...prev,
              {
                role: "tool",
                content: `[调用工具] ${data.name}`,
                tool_calls: [data],
              } as AgentMessage,
            ]);
          }
        },
        onSubagentToken: (text) => {
          setMessages((prev) => {
            const idx = findLastIndex(prev, (m) => m.role === "tool" && m.content.startsWith("[调用工具] task"));
            if (idx < 0) return prev;
            const updated = [...prev];
            const msg = updated[idx];
            updated[idx] = { ...msg, subagent_content: (msg.subagent_content ?? "") + text };
            return updated;
          });
        },
        onSubagentToolEvent: (event: SSEEvent) => {
          setMessages((prev) => {
            const idx = findLastIndex(prev, (m) => m.role === "tool" && m.content.startsWith("[调用工具] task"));
            if (idx < 0) return prev;
            const updated = [...prev];
            const msg = updated[idx];
            const steps: SubagentStep[] = [...(msg.subagent_steps ?? [])];
            const d = event.data as { name: string; result?: string };
            if (event.event === "subagent_tool_start") {
              steps.push({ type: "tool_start", name: d.name });
            } else {
              steps.push({ type: "tool_end", name: d.name, result: d.result });
            }
            updated[idx] = { ...msg, subagent_steps: steps };
            return updated;
          });
        },
        onContentStart: () => {
          if (partialContent) {
            const sealed = partialContent;
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && last?.id == null) {
                return [...prev.slice(0, -1), { ...last, content: sealed, id: -1 } as AgentMessage];
              }
              return prev;
            });
            partialContent = "";
          }
        },
        onDone: (data) => {
          setMessages((prev) => {
            const lastIdx = findLastIndex(prev, (m) => m.role === "assistant" && m.id == null);
            if (lastIdx >= 0) {
              const updated = [...prev];
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: partialContent || updated[lastIdx].content,
                id: -1,  // 标记为已完成，防止后续消息写入此气泡
                token_in: data.token_in,
                token_out: data.token_out,
                created_at: new Date().toISOString(),
              } as AgentMessage;
              return updated;
            }
            return prev;
          });
          setStreaming(false);
          abortRef.current = null;
        },
        onError: (errMsg) => {
          setError(errMsg);
          setStreaming(false);
          abortRef.current = null;
        },
        onRecursionLimit: (data) => {
          setMessages((prev) => {
            const lastIdx = findLastIndex(prev, (m) => m.role === "assistant" && m.id == null);
            if (lastIdx >= 0) {
              const updated = [...prev];
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: partialContent || updated[lastIdx].content,
                id: -1,  // 标记为已完成
                token_in: data.token_in,
                token_out: data.token_out,
                created_at: new Date().toISOString(),
              } as AgentMessage;
              return updated;
            }
            return prev;
          });
          setRecursionLimitHit(true);
          setStreaming(false);
          abortRef.current = null;
        },
      });

      abortRef.current = controller;
    }, 0);
  }, [conversationId]);

  const send = useCallback(
    (message: string) => {
      if (conversationId == null || streaming) return;

      // 立即追加用户消息到 UI
      const userMsg: AgentMessage = {
        role: "user",
        content: message,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // 创建流式中的 partial assistant 消息
      setStreaming(true);
      setError(null);
      setRecursionLimitHit(false);

      let partialContent = "";

      const controller = streamAgentChat(conversationId, message, {
        onToken: (text) => {
          partialContent += text;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant" && last?.id == null) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: partialContent },
              ];
            }
            return [
              ...prev,
              { role: "assistant", content: partialContent } as AgentMessage,
            ];
          });
        },
        onToolEvent: (event) => {
          if (event.event === "tool_start") {
            const data = event.data as { name: string; args: unknown };
            setMessages((prev) => [
              ...prev,
              {
                role: "tool",
                content: `[调用工具] ${data.name}`,
                tool_calls: [data],
              } as AgentMessage,
            ]);
          }
        },
        onSubagentToken: (text) => {
          setMessages((prev) => {
            const idx = findLastIndex(prev, (m) => m.role === "tool" && m.content.startsWith("[调用工具] task"));
            if (idx < 0) return prev;
            const updated = [...prev];
            const msg = updated[idx];
            updated[idx] = { ...msg, subagent_content: (msg.subagent_content ?? "") + text };
            return updated;
          });
        },
        onSubagentToolEvent: (event: SSEEvent) => {
          setMessages((prev) => {
            const idx = findLastIndex(prev, (m) => m.role === "tool" && m.content.startsWith("[调用工具] task"));
            if (idx < 0) return prev;
            const updated = [...prev];
            const msg = updated[idx];
            const steps: SubagentStep[] = [...(msg.subagent_steps ?? [])];
            const d = event.data as { name: string; result?: string };
            if (event.event === "subagent_tool_start") {
              steps.push({ type: "tool_start", name: d.name });
            } else {
              steps.push({ type: "tool_end", name: d.name, result: d.result });
            }
            updated[idx] = { ...msg, subagent_steps: steps };
            return updated;
          });
        },
        onContentStart: () => {
          if (partialContent) {
            const sealed = partialContent;
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && last?.id == null) {
                return [...prev.slice(0, -1), { ...last, content: sealed, id: -1 } as AgentMessage];
              }
              return prev;
            });
            partialContent = "";
          }
        },
        onDone: (data) => {
          setMessages((prev) => {
            const lastIdx = findLastIndex(prev, (m) => m.role === "assistant" && m.id == null);
            if (lastIdx >= 0) {
              const updated = [...prev];
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: partialContent || updated[lastIdx].content,
                id: -1,  // 标记为已完成，防止后续消息写入此气泡
                token_in: data.token_in,
                token_out: data.token_out,
                created_at: new Date().toISOString(),
              } as AgentMessage;
              return updated;
            }
            return prev;
          });
          setStreaming(false);
          abortRef.current = null;
        },
        onError: (errMsg) => {
          setError(errMsg);
          setStreaming(false);
          abortRef.current = null;
        },
        onRecursionLimit: (data) => {
          setMessages((prev) => {
            const lastIdx = findLastIndex(prev, (m) => m.role === "assistant" && m.id == null);
            if (lastIdx >= 0) {
              const updated = [...prev];
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: partialContent || updated[lastIdx].content,
                id: -1,  // 标记为已完成
                token_in: data.token_in,
                token_out: data.token_out,
                created_at: new Date().toISOString(),
              } as AgentMessage;
              return updated;
            }
            return prev;
          });
          setRecursionLimitHit(true);
          setStreaming(false);
          abortRef.current = null;
        },
      });

      abortRef.current = controller;
    },
    [conversationId, streaming]
  );

  // 清理流式连接
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const value: AgentSessionState = useMemo(
    () => ({
      sessionId,
      currentConversationId: conversationId,
      agentProfile,
      routeContextKey,
      productId,
      versionId,
      versionName,
      productName,
      projectBranches,
      conversations,
      messages,
      streaming,
      resolving,
      error,
      recursionLimitHit,
      resolve,
      send,
      loadHistory,
      cancel,
      continueGeneration,
      createNewConversation,
      switchConversation,
      loadConversations,
    }),
    [
      sessionId,
      conversationId,
      agentProfile,
      routeContextKey,
      productId,
      versionId,
      versionName,
      productName,
      projectBranches,
      conversations,
      messages,
      streaming,
      resolving,
      error,
      recursionLimitHit,
      resolve,
      send,
      loadHistory,
      cancel,
      continueGeneration,
      createNewConversation,
      switchConversation,
      loadConversations,
    ]
  );

  return (
    <AgentSessionContext.Provider value={value}>
      {children}
    </AgentSessionContext.Provider>
  );
}

export function useAgentSession(): AgentSessionState {
  const ctx = useContext(AgentSessionContext);
  if (!ctx) throw new Error("useAgentSession must be used inside AgentSessionProvider");
  return ctx;
}
