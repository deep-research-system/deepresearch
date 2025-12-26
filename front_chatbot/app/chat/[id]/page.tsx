// app/chat/[id]/page.tsx
"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { useChat } from "@/components/chat-provider"
import type { Agent } from "@/lib/chat-store"
import { readSseStream } from "@/lib/sse"

type PendingClarify = {
  originalQuestion: string
  questions: string[]
}

function parseClarifyAnswers(text: string, n: number): string[] {
  const answers = Array(n).fill("")
  const raw = (text ?? "").trim()
  if (!raw) return answers

  const lines = raw.split(/\r?\n/)

  // 1) 번호형 파싱: "1) ...", "1. ...", "1: ..."
  let cur = -1
  for (const line of lines) {
    const m = line.match(/^\s*(\d+)\s*[).:]\s*(.*)$/)
    if (m) {
      const idx = Math.max(0, Math.min(n - 1, Number(m[1]) - 1))
      cur = idx
      answers[cur] = (m[2] ?? "").trim()
      continue
    }
    if (cur >= 0) {
      const t = line.trim()
      if (!t) continue
      answers[cur] += (answers[cur] ? "\n" : "") + t
    }
  }
  if (answers.some((a) => a.trim())) return answers

  // 2) 빈 줄 블록 기준
  const blocks = raw
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (blocks.length >= 2) {
    for (let i = 0; i < n; i++) answers[i] = (blocks[i] ?? "").trim()
    return answers
  }

  // 3) 줄 단위 순서 매핑
  const nonEmptyLines = lines.map((l) => l.trim()).filter(Boolean)
  if (nonEmptyLines.length >= 2) {
    for (let i = 0; i < n; i++) answers[i] = (nonEmptyLines[i] ?? "").trim()
    if (nonEmptyLines.length > n && n >= 1) {
      answers[n - 1] = answers[n - 1] + "\n" + nonEmptyLines.slice(n).join("\n")
    }
    return answers
  }

  // 4) 한 덩어리면 모든 질문에 동일 답
  for (let i = 0; i < n; i++) answers[i] = raw
  return answers
}

/**
 * 채팅 ID 기반으로 "랜덤처럼 보이되" 새로고침해도 동일하게 유지되는 선택 로직
 */
function pickIntroLine(stableKey: string) {
  const intros = [
    "정확한 조사를 위해 몇 가지를 확인할게요.",
    "추가적으로 몇가지를 더 여쭤볼게요.",
    "원하시는 결과에 맞추려면 아래 정보가 필요해요.",
    "정확도를 높이기 위해 몇 가지만 빠르게 여쭤볼게요.",
  ]

  // 간단한 해시(외부 라이브러리 없이)
  let h = 0
  for (let i = 0; i < stableKey.length; i++) {
    h = (h * 31 + stableKey.charCodeAt(i)) >>> 0
  }
  return intros[h % intros.length]
}

function formatClarifyQuestions(qs: string[], stableKey: string) {
  const intro = pickIntroLine(stableKey)
  const list = qs.map((q, i) => `${i + 1}. ${q}`).join("\n")
  return `${intro}\n\n${list}`
}

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { chats, setChats, toggleSidebar } = useChat()
  const [isLoading, setIsLoading] = useState(false)

  const [pendingClarify, setPendingClarify] = useState<PendingClarify | null>(null)

  const chat = useMemo(() => chats.find((c) => c.id === id), [chats, id])
  if (!chat) {
    return (
      <>
        <ChatHeader title="Chat not found" onMenuClick={toggleSidebar} />
        <div className="flex-1 flex items-center justify-center">
          <button className="underline" onClick={() => router.push("/")}>
            홈으로 이동
          </button>
        </div>
      </>
    )
  }

  const API_URL = "http://localhost:8000/invoke/stream"

  const streamingAssistantIdRef = useRef<string | null>(null)
  const currentNodeRef = useRef<string | null>(null)
  const sendingRef = useRef(false)

  // 개발모드 StrictMode에서 useEffect 2회 호출 방지
  const autoSentRef = useRef(false)

  // "~~중..." 상태 전용 말풍선(임시)
  const statusMessageIdRef = useRef<string | null>(null)

  // end에서 status를 지울지 여부(오류는 남기기)
  const statusStickyRef = useRef(false)

  const releaseSendLock = () => {
    sendingRef.current = false
    setIsLoading(false)
  }

  const appendMessage = (role: "user" | "assistant", content: string) => {
    const m = {
      id: crypto.randomUUID(),
      role,
      content,
      createdAt: Date.now(),
    }

    setChats((prev) =>
      prev.map((c) =>
        c.id === id ? { ...c, messages: [...c.messages, m], updatedAt: Date.now() } : c,
      ),
    )

    return m.id
  }

  const pushUserMessage = (content: string) => {
    const m = {
      id: crypto.randomUUID(),
      role: "user" as const,
      content,
      createdAt: Date.now(),
    }

    setChats((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              messages: [...c.messages, m],
              title:
                c.title === "New Chat"
                  ? content.slice(0, 50) + (content.length > 50 ? "..." : "")
                  : c.title,
              updatedAt: Date.now(),
            }
          : c,
      ),
    )

    return m
  }

  const replaceMessageContent = (messageId: string, content: string) => {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== id) return c
        return {
          ...c,
          messages: c.messages.map((m) => (m.id === messageId ? { ...m, content } : m)),
          updatedAt: Date.now(),
        }
      }),
    )
  }

  const removeMessage = (messageId: string) => {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== id) return c
        return {
          ...c,
          messages: c.messages.filter((m) => m.id !== messageId),
          updatedAt: Date.now(),
        }
      }),
    )
  }

  const ensureStatusMessage = (text: string) => {
    const mid = statusMessageIdRef.current
    if (!mid) {
      const id = appendMessage("assistant", text)
      statusMessageIdRef.current = id
      return id
    }
    replaceMessageContent(mid, text)
    return mid
  }

  const clearStatusMessage = () => {
    const mid = statusMessageIdRef.current
    if (mid) {
      removeMessage(mid)
      statusMessageIdRef.current = null
    }
  }

  const ensureTypingPlaceholder = () => {
    if (streamingAssistantIdRef.current) return streamingAssistantIdRef.current
    const mid = appendMessage("assistant", "…")
    streamingAssistantIdRef.current = mid
    return mid
  }

  const appendAssistantDelta = (delta: string) => {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== id) return c
        const messages = [...c.messages]
        let msgId = streamingAssistantIdRef.current

        if (!msgId) {
          const nid = crypto.randomUUID()
          streamingAssistantIdRef.current = nid
          messages.push({
            id: nid,
            role: "assistant",
            content: delta,
            createdAt: Date.now(),
          })
          return { ...c, messages, updatedAt: Date.now() }
        }

        const idx = messages.findIndex((m) => m.id === msgId)
        if (idx === -1) {
          const nid = crypto.randomUUID()
          streamingAssistantIdRef.current = nid
          messages.push({
            id: nid,
            role: "assistant",
            content: delta,
            createdAt: Date.now(),
          })
          return { ...c, messages, updatedAt: Date.now() }
        }

        const prevText = messages[idx].content
        messages[idx] = {
          ...messages[idx],
          content: prevText === "…" ? delta : prevText + delta,
        }
        return { ...c, messages, updatedAt: Date.now() }
      }),
    )
  }

  const startStream = async (
    question: string,
    messagesForRequest: { role: string; content: string }[],
    clarifying_questions: string[] = [],
    clarifying_answers: string[] = [],
  ) => {
    streamingAssistantIdRef.current = null
    currentNodeRef.current = null

    // 새 스트림 시작 시: status는 기본적으로 end에서 제거되는 진행 표시
    statusStickyRef.current = false

    // 상태 말풍선 초기화
    clearStatusMessage()

    const initialMessage =
      clarifying_questions && clarifying_questions.length > 0
        ? "추가답변 분석중..."
        : "질문분석중..."
    ensureStatusMessage(initialMessage)

    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))

    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        messages: messagesForRequest,
        clarifying_questions,
        clarifying_answers,
      }),
    })

    if (!res.ok) {
      // 서버 오류는 사용자에게 남겨두는 편이 좋아서 sticky 처리
      statusStickyRef.current = true
      ensureStatusMessage(`서버 오류 (HTTP ${res.status})`)
      releaseSendLock()
      return
    }

    await readSseStream(res, (evt) => {
      switch (evt.event) {
        case "start":
          break

        case "node_update": {
          const msg = evt.data?.message || ""
          if (msg) ensureStatusMessage(String(msg))
          break
        }

        case "assistant": {
          const t = evt.data?.type

          if (t === "assistant_text" && evt.data?.content) {
            const sid = ensureTypingPlaceholder()
            // 토큰이 나오기 시작하면 진행 상태 말풍선은 제거
            clearStatusMessage()
            streamingAssistantIdRef.current = sid
            appendAssistantDelta(String(evt.data.content))
            break
          }

          if (t === "clarify_questions_done") {
            const qs: string[] = evt.data?.questions ?? []
            setPendingClarify({ originalQuestion: question, questions: qs })

            const text = formatClarifyQuestions(qs, String(id))

            // 중요: 추가질문은 "status 말풍선"이 아니라 "assistant 메시지"로 남긴다
            clearStatusMessage()
            appendMessage("assistant", text)

            streamingAssistantIdRef.current = null
            releaseSendLock()
            break
          }

          if (t === "final_question") {
            const questionText: string = String(evt.data?.question ?? evt.data?.content ?? "")
            streamingAssistantIdRef.current = null

            clearStatusMessage()

            if (questionText) {
              appendMessage("assistant", questionText)
            }

            // 다음 단계 진행 표시
            ensureStatusMessage("서브쿼리 생성중...")
            break
          }

          if (t === "subqueries_done") {
            const list: string[] = evt.data?.sub_queries ?? []
            streamingAssistantIdRef.current = null

            if (Array.isArray(list) && list.length > 0) {
              const text = list.map((q: string, i: number) => `${i + 1}. ${q}`).join("\n")
              appendMessage("assistant", text)
            }

            clearStatusMessage()
            break
          }

          if (evt.data?.content) {
            appendMessage("assistant", String(evt.data.content))
          }
          break
        }

        case "error": {
          // error는 사용자에게 남기는 게 유리
          statusStickyRef.current = true
          const msg = evt.data?.message ?? "알 수 없는 오류"
          ensureStatusMessage(`오류: ${msg}`)
          releaseSendLock()
          break
        }

        case "end": {
          // 진행중(status)만 정리하고, 오류(statusSticky)는 남긴다
          if (!statusStickyRef.current) clearStatusMessage()
          releaseSendLock()
          break
        }
      }
    })
  }

  const handleSend = (message: string) => {
    if (sendingRef.current) return
    if (isLoading) return

    const trimmed = (message ?? "").trim()
    if (!trimmed) return

    sendingRef.current = true
    setIsLoading(true)

    if (pendingClarify) {
      const pc = pendingClarify
      setPendingClarify(null)

      const userMsg = pushUserMessage(trimmed)
      const answers = parseClarifyAnswers(trimmed, pc.questions.length)

      const messagesForRequest = [...chat.messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }))

      startStream(pc.originalQuestion, messagesForRequest, pc.questions, answers).catch((e) => {
        console.error("SSE 오류:", e)
        appendMessage("assistant", "스트리밍 중 오류가 발생했습니다.")
        releaseSendLock()
      })
      return
    }

    const userMsg = pushUserMessage(trimmed)
    const messagesForRequest = [...chat.messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
    }))

    startStream(trimmed, messagesForRequest).catch((e) => {
      console.error("SSE 오류:", e)
      appendMessage("assistant", "스트리밍 중 오류가 발생했습니다.")
      releaseSendLock()
    })
  }

  const handleAgentChange = (agent: Agent) => {
    setChats((prev) =>
      prev.map((c) => (c.id === id ? { ...c, agent, updatedAt: Date.now() } : c)),
    )
  }

  useEffect(() => {
    if (!chat) return
    if (autoSentRef.current) return

    const key = `pending-message-${id}`
    let pending = ""

    try {
      pending = (localStorage.getItem(key) ?? "").trim()
      if (pending) localStorage.removeItem(key)
    } catch {
      return
    }

    if (!pending) return
    autoSentRef.current = true

    const exists = chat.messages.some(
      (m) => m.role === "user" && String(m.content ?? "").trim() === pending,
    )
    if (exists) return

    setTimeout(() => {
      handleSend(pending)
    }, 0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat, id])

  return (
    <>
      <ChatHeader title={chat.title} onMenuClick={toggleSidebar} />
      <MessageList messages={chat.messages} />
      <ChatInput
        onSend={handleSend}
        disabled={isLoading}
        agent={chat.agent}
        onAgentChange={handleAgentChange}
      />
    </>
  )
}
