import { useCallback, useEffect, useState } from "react";
import { listConversations } from "./api";
import type { ConversationResponse } from "./types";

export function useConversations(token: string) {
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);

  const refresh = useCallback(async () => {
    try {
      const data = await listConversations(token);
      setConversations(data);
    } catch {
      return;
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { conversations, refresh };
}
