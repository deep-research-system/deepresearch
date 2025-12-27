"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"

import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { useChat } from "@/components/chat-provider"

import { readSseStream } from "@/lib/sse"

type Agent = "General" | "DeepResearch" | "MeetingSummary"

type PendingClarify = {
  originalQuestion: string
  questions: string[]
}

// 디버그용: 내부 이벤트(final_question/subqueries)를 화면에 찍을지
const DEBUG_SHOW_INTERNAL = true

function now() {
  return Date.now()
}

function newId() {
  return crypto.randomUUID()
}

function formatClarifyBlock(qs: string[]) {
  const lines = ["조사 주제를 명확히 하기 위해 몇 가지 질문을 드릴게요."]
  qs.slice(0, 3).forEach((q, i) => lines.push(`${i + 1}) ${q}`))
  return lines.join("\n")
}

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { chats, setChats, toggleSidebar } = useChat()

  const chat = useMemo(() => chats.find((c) => c.id === id), [chats, id])
  const [isLoading, setIsLoading] = useState(false)

  // “현재 추가질문이 대기 중인지”를 프론트가 들고 있다가 다음 요청에 실어 보냄
  const pendingClarifyRef = useRef<PendingClarify | null>(null)

  // 같은 요청(턴)에서 assistant 메시지에 누적 스트리밍하기 위한 turn id
  const turnIdRef = useRef<string>("")

  // 중복 전송 방지
  const sendLockRef = useRef(false)

  // statusText를 고정할지(에러 등) 제어
  const statusStickyRef = useRef(false)

  // 현재 턴에서 assistant_text를 “한 번이라도” 받았는지
  const gotAssistantTextRef = useRef(false)

  // 백엔드 엔드포인트
  const API_URL = "http://localhost:8000/invoke/stream"

  useEffect(() => {
    if (!chat) router.replace("/")
  }, [chat, router])

  function updateChatMessages(updater: (prev: any[]) => any[]) {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== id) return c
        const nextMessages = updater(c.messages)
        return { ...c, messages: nextMessages, updatedAt: now() }
      })
    )
  }

  function addUserMessage(content: string) {
    updateChatMessages((prev) => [
      ...prev,
      { id: newId(), role: "user", content, createdAt: now() },
    ])
  }

  function ensureAssistantMessage(turnId: string, initialStatus = "") {
    updateChatMessages((prev) => {
      const exists = prev.some((m) => m.role === "assistant" && m.turnId === turnId)
      if (exists) return prev
      return [
        ...prev,
        {
          id: newId(),
          role: "assistant",
          turnId,
          statusText: initialStatus,
          body: "",
          createdAt: now(),
        },
      ]
    })
  }

  function setAssistantStatus(turnId: string, text: string) {
    updateChatMessages((prev) =>
      prev.map((m) => {
        if (m.role !== "assistant") return m
        if (m.turnId !== turnId) return m
        if (statusStickyRef.current) return m
        return { ...m, statusText: text }
      })
    )
  }

  function appendAssistantText(turnId: string, chunk: string) {
    updateChatMessages((prev) =>
      prev.map((m) => {
        if (m.role !== "assistant") return m
        if (m.turnId !== turnId) return m
        return { ...m, body: (m.body || "") + chunk }
      })
    )
  }

  function releaseSendLock() {
    sendLockRef.current = false
    setIsLoading(false)
  }

  async function startStream(turnId: string, params: {
    question: string
    messages: { role: string; content: string }[]
    clarifying_questions: string[]
    clarifying_answers: string[]
  }) {
    let ended = false

    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })

    if (!res.ok) {
      statusStickyRef.current = true
      setAssistantStatus(turnId, `서버 오류 (HTTP ${res.status})`)
      releaseSendLock()
      return
    }

    try {
      await readSseStream(res, (evt) => {
        // 디버깅 로그
        console.log("[SSE]", evt.event, evt.data)

        if (evt.event === "start") {
          const msg = evt.data?.message ?? "시작"
          setAssistantStatus(turnId, msg)
          return
        }

        if (evt.event === "node_update") {
          const msg = evt.data?.message ?? ""
          if (msg) setAssistantStatus(turnId, msg)
          return
        }

        if (evt.event === "assistant") {
          const data = evt.data || {}
          const t = data.type

          // 1) 실시간 스트리밍 텍스트
          if (t === "assistant_text") {
            const chunk = (data.content ?? "").toString()
            if (chunk) {
              gotAssistantTextRef.current = true
              appendAssistantText(turnId, chunk)
            }
            return
          }

          // 2) 추가질문 리스트(저장용 + (필요시) 화면표시)
          if (t === "clarify_questions" || t === "clarify_questions_done") {
            const qs: string[] = Array.isArray(data.questions) ? data.questions : []
            if (qs.length > 0) {
              pendingClarifyRef.current = {
                originalQuestion: params.question,
                questions: qs,
              }

              // 백엔드가 안내문/질문을 assistant_text로 안 흘려주는 케이스 대비:
              // (NO_QUESTION 필터링, LLM 출력형식 불안정 등)
              if (!gotAssistantTextRef.current) {
                appendAssistantText(turnId, formatClarifyBlock(qs))
                gotAssistantTextRef.current = true
              }
            }
            return
          }

          // 3) 최종 질문(디버그로 화면 표시)
          if (t === "final_question") {
            const fq = (data.question ?? "").toString().trim()
            if (DEBUG_SHOW_INTERNAL && fq) {
              const block = `\n\n[final_question]\n${fq}\n`
              appendAssistantText(turnId, block)
              gotAssistantTextRef.current = true
            }
            return
          }

          // 4) 서브쿼리(디버그로 화면 표시)
          if (t === "subqueries_done") {
            const subqs: string[] = Array.isArray(data.sub_queries) ? data.sub_queries : []
            if (DEBUG_SHOW_INTERNAL && subqs.length > 0) {
              const block =
                `\n\n[subqueries_done]\n` +
                subqs.map((q, i) => `${i + 1}) ${q}`).join("\n") +
                "\n"
              appendAssistantText(turnId, block)
              gotAssistantTextRef.current = true
            }
            return
          }

          return
        }

        if (evt.event === "error") {
          const msg = evt.data?.message ?? "알 수 없는 에러"
          statusStickyRef.current = true
          setAssistantStatus(turnId, `에러: ${msg}`)
          return
        }

        if (evt.event === "end") {
          ended = true

          // “아무 내용도 안 찍힌” 케이스 방지(사용자 체감)
          if (!gotAssistantTextRef.current && DEBUG_SHOW_INTERNAL) {
            appendAssistantText(turnId, "\n\n(표시할 출력이 없습니다. final_question/subqueries 출력 로직을 확인하세요)\n")
          }

          releaseSendLock()
          return
        }
      })
    } catch (e: any) {
      statusStickyRef.current = true
      setAssistantStatus(turnId, `스트림 처리 실패: ${e?.message ?? String(e)}`)
      releaseSendLock()
    } finally {
      // readSseStream이 end 이벤트 없이 종료되는 경우 대비
      if (!ended) releaseSendLock()
    }
  }

  async function handleSend(text: string, _agent: Agent) {
    if (!chat) return
    if (sendLockRef.current) return

    const trimmed = (text ?? "").trim()
    if (!trimmed) return

    sendLockRef.current = true
    statusStickyRef.current = false
    gotAssistantTextRef.current = false
    setIsLoading(true)

    // 요청 전에 기존 히스토리만 구성(이번에 입력한 text는 question으로 따로 보냄)
    const messagesForRequest =
      (chat.messages || [])
        .filter((m: any) => m.role === "user" || m.role === "assistant")
        .map((m: any) => {
          if (m.role === "assistant") return { role: "assistant", content: m.body || "" }
          return { role: "user", content: m.content || "" }
        }) ?? []

    // UI에 먼저 user 메시지 추가
    addUserMessage(trimmed)

    // assistant placeholder 생성
    const turnId = newId()
    turnIdRef.current = turnId
    ensureAssistantMessage(turnId, "질문분석중...")

    // 1) “추가질문 답변 제출” 모드
    const pending = pendingClarifyRef.current
    if (pending && pending.questions.length > 0) {
      try {
        await startStream(turnId, {
          question: pending.originalQuestion,
          messages: messagesForRequest,
          clarifying_questions: pending.questions,
          clarifying_answers: [trimmed],
        })
        // 일단 pending 해제(서버가 followup을 주면 다시 세팅됨)
        pendingClarifyRef.current = null
      } catch (e: any) {
        statusStickyRef.current = true
        setAssistantStatus(turnId, `요청 실패: ${e?.message ?? String(e)}`)
        releaseSendLock()
      }
      return
    }

    // 2) 일반 질문 모드
    try {
      await startStream(turnId, {
        question: trimmed,
        messages: messagesForRequest,
        clarifying_questions: [],
        clarifying_answers: [],
      })
    } catch (e: any) {
      statusStickyRef.current = true
      setAssistantStatus(turnId, `요청 실패: ${e?.message ?? String(e)}`)
      releaseSendLock()
    }
  }

  if (!chat) return null

  return (
    <div className="flex h-full w-full">
      <div className="flex min-w-0 flex-1 flex-col">
        <ChatHeader title={chat.title} onMenuClick={toggleSidebar} />

        <div className="flex-1 overflow-hidden">
          <MessageList messages={chat.messages} />
        </div>

        <div className="border-t">
          <ChatInput
            disabled={isLoading}
            agent={chat.agent}
            onAgentChange={(a) => {
              setChats((prev) =>
                prev.map((c) => (c.id === chat.id ? { ...c, agent: a, updatedAt: now() } : c))
              )
            }}
            onSend={(t) => handleSend(t, chat.agent)}
          />
        </div>
      </div>
    </div>
  )
}
