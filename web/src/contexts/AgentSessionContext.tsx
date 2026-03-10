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
  type AgentMessage,
} from "../api/client";

function getOrCreateSessionId(): string {
  const KEY = "neodev_agent_session_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
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
  messages: AgentMessage[];
  streaming: boolean;
  resolving: boolean;
  error: string | null;
  resolve: (routeContextKey: string, projectId?: number | null, productId?: number | null) => Promise<void>;
  send: (message: string) => void;
  loadHistory: () => Promise<void>;
  cancel: () => void;
}

const AgentSessionContext = createContext<AgentSessionState | null>(null);

export function AgentSessionProvider({ children }: { children: ReactNode }) {
  const sessionId = useMemo(() => getOrCreateSessionId(), []);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [agentProfile, setAgentProfile] = useState<string | null>(null);
  const [routeContextKey, setRouteContextKey] = useState<string | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const resolve = useCallback(
    async (ctxKey: string, projectId?: number | null, prdId?: number | null) => {
      // 如果已经在同一个上下文中，跳过
      if (ctxKey === routeContextKey && conversationId != null && (prdId ?? null) === productId) return;

      setResolving(true);
      setError(null);
      try {
        const conv = await resolveAgentSession(sessionId, ctxKey, projectId, prdId);
        setConversationId(conv.conversation_id);
        setAgentProfile(conv.agent_profile);
        setRouteContextKey(conv.route_context_key);
        setProductId(conv.product_id ?? null);
        // 加载历史消息
        const { messages: history } = await getAgentMessages(conv.conversation_id);
        setMessages(history);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setResolving(false);
      }
    },
    [sessionId, routeContextKey, conversationId, productId]
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

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
  }, []);

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

      let partialContent = "";

      const controller = streamAgentChat(conversationId, message, {
        onToken: (text) => {
          partialContent += text;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant" && last?.id == null) {
              // 更新流式中的 partial 消息
              return [
                ...prev.slice(0, -1),
                { ...last, content: partialContent },
              ];
            }
            // 首次 token，追加 partial 消息
            return [
              ...prev,
              { role: "assistant", content: partialContent } as AgentMessage,
            ];
          });
        },
        onToolEvent: (event) => {
          // 工具事件作为系统消息附加显示
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
        onDone: (data) => {
          // 替换 partial 消息为完整版
          setMessages((prev) => {
            const filtered = prev.filter(
              (m) => !(m.role === "assistant" && m.id == null)
            );
            return [
              ...filtered,
              {
                role: "assistant",
                content: data.content,
                token_in: data.token_in,
                token_out: data.token_out,
                created_at: new Date().toISOString(),
              } as AgentMessage,
            ];
          });
          setStreaming(false);
          abortRef.current = null;
        },
        onError: (errMsg) => {
          setError(errMsg);
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
      messages,
      streaming,
      resolving,
      error,
      resolve,
      send,
      loadHistory,
      cancel,
    }),
    [
      sessionId,
      conversationId,
      agentProfile,
      routeContextKey,
      productId,
      messages,
      streaming,
      resolving,
      error,
      resolve,
      send,
      loadHistory,
      cancel,
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
