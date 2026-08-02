import { type FormEvent, useEffect, useRef, useState } from "react";
import type { ChatMessage, Pipeline } from "../types";

interface Props {
  messages: ChatMessage[];
  connected: boolean;
  sending: boolean;
  ask: (question: string) => void;
  pipeline: Pipeline;
  setPipeline: (pipeline: Pipeline) => void;
}

export function Chat({
  messages,
  connected,
  sending,
  ask,
  pipeline,
  setPipeline,
}: Props) {
  const [question, setQuestion] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || sending) return;
    ask(question.trim());
    setQuestion("");
  }

  return (
    <div className="card chat">
      <h2>
        Chat {!connected && <span className="badge status-failed">disconnected</span>}
      </h2>
      <div className="mode-toggle">
        <button
          type="button"
          disabled={sending}
          className={pipeline === "simple" ? "active-mode" : ""}
          onClick={() => setPipeline("simple")}
        >
          Simple
        </button>
        <button
          type="button"
          disabled={sending}
          className={pipeline === "agent" ? "active-mode" : ""}
          onClick={() => setPipeline("agent")}
        >
          Agent
        </button>
      </div>
      <div className="messages">
        {messages.length === 0 && (
          <p className="empty">Ask a question about the ingested documents.</p>
        )}
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.author}`}>
            <p>
              {message.author === "assistant" && message.pipeline === "agent" && (
                <span className="badge pipeline-badge">agent</span>
              )}
              {message.text}
              {message.inProgress && <span className="blinking-cursor">▍</span>}
            </p>
            {message.sources && message.sources.length > 0 && (
              <ul className="sources">
                {message.sources.map((source, index) => (
                  <li key={index} title={source.excerpt}>
                    [{index + 1}] {source.document_name}
                    {source.page ? ` (p. ${source.page})` : ""} · score{" "}
                    {source.score.toFixed(2)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form className="form-row" onSubmit={handleSubmit}>
        <input
          placeholder="Your question..."
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={!connected}
        />
        <button type="submit" disabled={!connected || sending}>
          Send
        </button>
      </form>
    </div>
  );
}
