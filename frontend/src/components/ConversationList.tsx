import { useState } from "react";
import { deleteConversation, getConversation } from "../api";
import type { ChatMessage, ConversationResponse } from "../types";

interface Props {
  token: string;
  conversations: ConversationResponse[];
  refresh: () => void;
  conversationId: string;
  setConversationId: (id: string) => void;
  loadHistory: (messages: ChatMessage[]) => void;
  clear: () => void;
  sending: boolean;
}

export function ConversationList({
  token,
  conversations,
  refresh,
  conversationId,
  setConversationId,
  loadHistory,
  clear,
  sending,
}: Props) {
  const [error, setError] = useState<string | null>(null);

  function newConversation() {
    setConversationId(crypto.randomUUID());
    clear();
  }

  async function handleSelect(id: string) {
    if (id === conversationId || sending) return;
    setError(null);
    try {
      const detail = await getConversation(token, id);
      const messages: ChatMessage[] = detail.turns.flatMap(
        (turn): ChatMessage[] => [
          { id: crypto.randomUUID(), author: "user", text: turn.question },
          {
            id: crypto.randomUUID(),
            author: "assistant",
            text: turn.answer,
            sources: turn.sources,
          },
        ],
      );
      loadHistory(messages);
      setConversationId(id);
    } catch {
      setError("Unable to load this conversation.");
    }
  }

  async function handleDelete(id: string) {
    if (id === conversationId && sending) return;
    setError(null);
    try {
      await deleteConversation(token, id);
      if (id === conversationId) {
        newConversation();
      }
      refresh();
    } catch {
      setError("Unable to delete this conversation.");
    }
  }

  return (
    <div className="card conversations">
      <div className="conversations-header">
        <h2>Conversations</h2>
        <button type="button" disabled={sending} onClick={newConversation}>
          New conversation
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <ul className="conversation-list">
        {conversations.length === 0 && (
          <p className="empty">No conversations yet.</p>
        )}
        {conversations.map((conversation) => (
          <li
            key={conversation.id}
            className={
              conversation.id === conversationId ? "active-conversation" : ""
            }
            onClick={() => handleSelect(conversation.id)}
          >
            <div>
              <span>{new Date(conversation.updated_at).toLocaleString()}</span>
              <span className="detail"> · {conversation.total_turns} turn(s)</span>
            </div>
            <button
              type="button"
              disabled={conversation.id === conversationId && sending}
              onClick={(event) => {
                event.stopPropagation();
                handleDelete(conversation.id);
              }}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
