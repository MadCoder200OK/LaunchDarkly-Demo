// Chat UI only. Python returns explicit live/fallback attribution and safe per-answer metadata.
import { useLayoutEffect, useRef, useState } from "react";
import { MessageCircle, X, ArrowUp, Sparkles } from "lucide-react";
import { api } from "../services/api";

// DEMO START chat-panel: Present independent AI questions, variation attribution, fallbacks, and scroll-aware replies.
export default function Assistant({ profileKey, aiStatus }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const conversation = useRef(null);
  const followingLatest = useRef(true);
  useLayoutEffect(() => {
    // Follow incoming answers while reading the latest turn; retain deliberate history scrolling.
    if (open && followingLatest.current && conversation.current) {
      conversation.current.scrollTop = conversation.current.scrollHeight;
    }
  }, [open, messages, busy]);
  function trackScroll() {
    const log = conversation.current;
    followingLatest.current =
      log.scrollHeight - log.scrollTop - log.clientHeight <= 48;
  }
  async function send(event) {
    // Send only the selected fictional identity and question; prevent duplicate pending requests.
    event.preventDefault();
    if (!message.trim() || busy) return;
    const question = message.trim();
    // Sending a new question explicitly resumes following its loading state and answer.
    followingLatest.current = true;
    setMessage("");
    setMessages((previous) => [...previous, { role: "user", text: question }]);
    setBusy(true);
    try {
      const result = await api.chat(profileKey, question);
      setMessages((previous) => [
        ...previous,
        { role: "assistant", text: result.reply, metadata: result },
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        { role: "assistant", text: error.message },
      ]);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button
        className="chat-launch"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label="Toggle offer assistant"
      >
        <MessageCircle size={20} /> Let's talk <span>↗</span>
      </button>
      {/* Exclude the entire chat panel from replay; network bodies and headers are disabled too. */}
      {open && (
        <aside data-private className="chat-panel" aria-label="Offer assistant">
          <header>
            <Sparkles size={19} />
            <strong>Your offer companion</strong>
            <button
              className="icon-button"
              aria-label="Close assistant"
              onClick={() => setOpen(false)}
            >
              <X size={18} />
            </button>
          </header>
          <div className="chat-disclaimer">
            {aiStatus?.status === "sdk_ready"
              ? "AI offer companion · fictional offers only"
              : "Scripted preview · AI is not ready"}
          </div>
          <div
            className="chat-messages"
            ref={conversation}
            onScroll={trackScroll}
            aria-live="polite"
          >
            <p className="bubble assistant">
              Hi! What would you like to know about our fictional offers?
            </p>
            {messages.map((entry, index) => (
              <div key={index} className={`bubble ${entry.role}`}>
                <p>{entry.text}</p>
                {entry.metadata && (
                  <small className="answer-metadata">
                    {entry.metadata.source}
                    {entry.metadata.fallback_message && (
                      <>
                        <br />
                        {entry.metadata.fallback_message}
                      </>
                    )}
                    {entry.metadata.fallback &&
                      entry.metadata.attempt_usage?.total != null && (
                        <>
                          <br />
                          Model attempt: {
                            entry.metadata.attempt_usage.total
                          }{" "}
                          tokens
                        </>
                      )}
                    {!entry.metadata.fallback && (
                      <>
                        <br />
                        {entry.metadata.model} · {entry.metadata.variation} v
                        {entry.metadata.version}
                        <br />
                        {entry.metadata.duration_ms} ms ·{" "}
                        {entry.metadata.usage?.total ?? "—"} tokens
                      </>
                    )}
                  </small>
                )}
              </div>
            ))}
            {busy && <p className="bubble assistant">Preparing your answer…</p>}
          </div>
          <form onSubmit={send}>
            <input
              aria-label="Your question"
              maxLength={1000}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask about an offer…"
            />
            <button
              className="send-button"
              disabled={busy || !message.trim()}
              aria-label="Send question"
            >
              <ArrowUp size={18} />
            </button>
          </form>
        </aside>
      )}
    </>
  );
}
// DEMO END chat-panel
