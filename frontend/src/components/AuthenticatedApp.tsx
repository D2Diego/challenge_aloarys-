import { useEffect, useRef, useState } from "react";
import { API_URL } from "../api";
import { useChat } from "../useChat";
import { useConversations } from "../useConversations";
import { Chat } from "./Chat";
import { ConversationList } from "./ConversationList";
import { DocumentManager } from "./DocumentManager";

const CONVERSATION_ID_KEY = "rag_conversation_id";

function readOrCreateConversationId(): string {
  const existing = sessionStorage.getItem(CONVERSATION_ID_KEY);
  if (existing) return existing;
  const newId = crypto.randomUUID();
  sessionStorage.setItem(CONVERSATION_ID_KEY, newId);
  return newId;
}

interface Props {
  token: string;
  onLogout: () => void;
}

export function AuthenticatedApp({ token, onLogout }: Props) {
  const [conversationId, setConversationIdState] = useState(
    readOrCreateConversationId,
  );
  const { conversations, refresh } = useConversations(token);
  const { messages, connected, sending, ask, loadHistory, clear } = useChat(
    token,
    conversationId,
  );

  function setConversationId(id: string) {
    sessionStorage.setItem(CONVERSATION_ID_KEY, id);
    setConversationIdState(id);
  }

  const previouslySendingRef = useRef(false);
  useEffect(() => {
    if (previouslySendingRef.current && !sending) {
      refresh();
    }
    previouslySendingRef.current = sending;
  }, [sending, refresh]);

  return (
    <div className="app">
      <header>
        <h1>AI Document Analyst</h1>
        <div className="header-actions">
          <a
            className="link"
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            API docs
          </a>
          <button className="link" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="layout-with-sidebar">
        <ConversationList
          token={token}
          conversations={conversations}
          refresh={refresh}
          conversationId={conversationId}
          setConversationId={setConversationId}
          loadHistory={loadHistory}
          clear={clear}
          sending={sending}
        />
        <div className="layout">
          <DocumentManager token={token} />
          <Chat
            messages={messages}
            connected={connected}
            sending={sending}
            ask={ask}
          />
        </div>
      </main>
    </div>
  );
}
