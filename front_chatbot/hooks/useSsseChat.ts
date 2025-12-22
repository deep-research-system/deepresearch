// hooks/useSseChat.ts
import { useCallback, useRef, useState } from "react";
import { readSseStream, type SseEvent } from "@/lib/sse";

// 채팅 메시지 타입 정의
export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
};

// 고유 ID 생성 유틸
function newId() {
  // Date.now()만 쓰면 중복될 수 있으니 UUID 권장
  return crypto.randomUUID();
}

// SSE 기반 채팅 훅
export function useSseChat(apiBaseUrl = "http://localhost:8000") {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // 진행상태 메시지를 "업데이트"하고 싶을 때 쓸 수 있는 ref
  const lastProgressIdRef = useRef<string | null>(null);

  const appendMessage = useCallback((msg: Omit<ChatMessage, "id">) => {
    setMessages((prev) => [...prev, { id: newId(), ...msg }]);
  }, []);

  const upsertProgress = useCallback((text: string) => {
    setMessages((prev) => {
      const id = lastProgressIdRef.current;
      if (!id) {
        const newMsg: ChatMessage = { id: newId(), role: "system", content: text };
        lastProgressIdRef.current = newMsg.id;
        return [...prev, newMsg];
      }
      return prev.map((m) => (m.id === id ? { ...m, content: text } : m));
    });
  }, []);

  const handleEvent = useCallback(
    (evt: SseEvent) => {
      switch (evt.event) {
        case "start":
          appendMessage({ role: "system", content: evt.data?.message ?? "stream started" });
          return;

        case "node_update":
          // 노드 진행은 "새 메시지"로 계속 쌓지 말고, 한 줄을 업데이트하는 게 UX가 좋음
          upsertProgress(evt.data?.message ?? `[${evt.data?.node}] working...`);
          return;

        case "assistant":
          // 서버에서 assistant 이벤트는 다양한 type을 가질 수 있음
          // 우선 content 중심으로 표시
          if (evt.data?.type === "clarify_questions") {
            const qs: string[] = evt.data?.questions ?? [];
            appendMessage({
              role: "assistant",
              content: `${evt.data?.content ?? "추가 질문입니다."}\n\n- ${qs.join("\n- ")}`,
            });
          } else {
            appendMessage({
              role: "assistant",
              content: evt.data?.content ?? JSON.stringify(evt.data),
            });
          }
          return;

        case "error":
          appendMessage({
            role: "system",
            content: `ERROR(${evt.data?.type ?? "Error"}): ${evt.data?.message ?? "unknown"}`,
          });
          return;

        case "end":
          appendMessage({ role: "system", content: evt.data?.message ?? "stream finished" });
          // 진행상태 메시지 리셋(다음 요청 때 새로 만들기)
          lastProgressIdRef.current = null;
          return;

        default:
          // 알 수 없는 이벤트는 로그용으로 표시하거나 무시
          return;
      }
    },
    [appendMessage, upsertProgress]
  );

  const send = useCallback(
    async (question: string) => {
      appendMessage({ role: "user", content: question });
      setIsStreaming(true);

      const res = await fetch(`${apiBaseUrl}/invoke/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          // 지금은 최소로. 너의 스키마에 맞춰 필요하면 채워라.
          messages: [],
          clarifying_questions: [],
          clarifying_answers: [],
        }),
      });

      if (!res.ok) {
        setIsStreaming(false);
        appendMessage({ role: "system", content: `HTTP ${res.status}` });
        return;
      }

      try {
        await readSseStream(res, handleEvent);
      } finally {
        setIsStreaming(false);
      }
    },
    [apiBaseUrl, appendMessage, handleEvent]
  );

  return { messages, isStreaming, send, setMessages };
}
