import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL } from "./api";
import type { ChatEvent, ChatMessage } from "./types";

function newId(): string {
  return crypto.randomUUID();
}

export function useChat(token: string, conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [sending, setSending] = useState(false);
  const websocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const websocket = new WebSocket(`${WS_URL}/ws/chat`);
    websocketRef.current = websocket;

    websocket.onopen = () => {
      websocket.send(JSON.stringify({ token, conversation_id: conversationId }));
      setConnected(true);
    };

    websocket.onclose = () => setConnected(false);

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data) as ChatEvent;

      if (data.type === "token") {
        setMessages((current) => {
          const copy = [...current];
          const last = copy[copy.length - 1];
          if (last?.author === "assistant" && last.inProgress) {
            copy[copy.length - 1] = { ...last, text: last.text + data.text };
          }
          return copy;
        });
      } else if (data.type === "complete") {
        setMessages((current) => {
          const copy = [...current];
          const last = copy[copy.length - 1];
          if (last?.author === "assistant" && last.inProgress) {
            copy[copy.length - 1] = {
              ...last,
              text: data.answer,
              sources: data.sources,
              inProgress: false,
            };
          }
          return copy;
        });
        setSending(false);
      } else if (data.type === "error") {
        setMessages((current) => {
          const copy = [...current];
          const last = copy[copy.length - 1];
          if (last?.author === "assistant" && last.inProgress) {
            copy[copy.length - 1] = {
              ...last,
              text: `Error: ${data.message}`,
              inProgress: false,
            };
          }
          return copy;
        });
        setSending(false);
      }
    };

    return () => websocket.close();
  }, [token, conversationId]);

  const ask = useCallback((question: string) => {
    const websocket = websocketRef.current;
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;

    setMessages((current) => [
      ...current,
      { id: newId(), author: "user", text: question },
      { id: newId(), author: "assistant", text: "", inProgress: true },
    ]);
    setSending(true);
    websocket.send(JSON.stringify({ question }));
  }, []);

  const loadHistory = useCallback((history: ChatMessage[]) => {
    setMessages(history);
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, connected, sending, ask, loadHistory, clear };
}
