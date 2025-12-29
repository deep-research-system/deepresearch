"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"

import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { useChat } from "@/components/chat-provider"

import { readSseStream } from "@/lib/sse"
import type { Agent } from "@/lib/chat-store"

type PendingClarify = {
  originalQuestion: string
  questions: string[]
  answers: string[]
}

const DEBUG_SHOW_INTERNAL = true
const API_URL = "http://localhost:8000/deepresearch"

function now() {
  return Date.now()
}
function newId() {
  return crypto.randomUUID()
}

function formatClarifyBlock(qnaMent: string | null, qs: string[]) {
  const lines: string[] = []
  if (qnaMent && qnaMent.trim()) lines.push(qnaMent.trim())
  else lines.push("조사 주제를 명확히 하기 위해 몇 가지 질문을 드릴게요.")
  qs.slice(0, 10).forEach((q, i) => lines.push(`${i + 1}) ${q}`))
  return lines.join("\n")
}

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const sp = useSearchParams()
  const qFromUrl = (sp.get("q") || "").trim()

  const { chats, setChats, toggleSidebar } = useChat()
  const chat = useMemo(() => chats.find((c) => c.id === id), [chats, id])

  const [isLoading, setIsLoading] = useState(false)

  const pendingClarifyRef = useRef<PendingClarify | null>(null)
  const sendLockRef = useRef(false)
  const statusStickyRef = useRef(false)
  const gotAnyAssistantContentRef = useRef(false)

  useEffect(() => {
    if (!chat) router.replace("/")
  }, [chat, router])

  function updateChatMessages(chatId: string, updater: (prev: any[]) => any[]) {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== chatId) return c
        const nextMessages = updater(c.messages)
        return { ...c, messages: nextMessages, updatedAt: now() }
      }),
    )
  }

  function ensureAssistantMessage(chatId: string, turnId: string, initialStatus = "") {
    updateChatMessages(chatId, (prev) => {
      const exists = prev.some((m: any) => m.role === "assistant" && m.turnId === turnId)
      if (exists) return prev
      return [
        ...prev,
        { id: newId(), role: "assistant", turnId, statusText: initialStatus, content: "", createdAt: now() },
      ]
    })
  }

  function setAssistantStatus(chatId: string, turnId: string, text: string) {
    updateChatMessages(chatId, (prev) =>
      prev.map((m: any) => {
        if (m.role !== "assistant") return m
        if (m.turnId !== turnId) return m
        if (statusStickyRef.current) return m
        return { ...m, statusText: text }
      }),
    )
  }

  function appendAssistantText(chatId: string, turnId: string, chunk: string) {
    updateChatMessages(chatId, (prev) =>
      prev.map((m: any) => {
        if (m.role !== "assistant") return m
        if (m.turnId !== turnId) return m
        return { ...m, content: (m.content || "") + chunk }
      }),
    )
  }

  function addUserMessage(chatId: string, content: string) {
    updateChatMessages(chatId, (prev) => [...prev, { id: newId(), role: "user", content, createdAt: now() }])
  }

  function releaseSendLock() {
    sendLockRef.current = false
    setIsLoading(false)
  }

  // 요청 직전에 최신 messages를 다시 꺼내기
  function getLatestMessagesFor(chatId: string) {
    const latestChat = chats.find((c) => c.id === chatId)
    const msgs = latestChat?.messages || []
    return msgs.map((m: any) => ({ role: m.role, content: m.content || "" }))
  }

  async function startStream(chatId: string, turnId: string, params: any) {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })

    if (!res.ok) {
      statusStickyRef.current = true
      setAssistantStatus(chatId, turnId, `서버 오류 (HTTP ${res.status})`)
      releaseSendLock()
      return
    }

    let ended = false

    try {
      await readSseStream(res, (evt) => {
        console.log("[SSE]", evt.event, evt.data)

        if (evt.event === "start") {
          setAssistantStatus(chatId, turnId, evt.data?.message ?? "시작")
          return
        }
        if (evt.event === "node_update") {
          const msg = evt.data?.message ?? ""
          if (msg) setAssistantStatus(chatId, turnId, msg)
          return
        }
        if (evt.event === "error") {
          statusStickyRef.current = true
          setAssistantStatus(chatId, turnId, `에러: ${evt.data?.message ?? "unknown"}`)
          return
        }
        if (evt.event === "end") {
          ended = true
          releaseSendLock()
          return
        }

        // ✅ 백엔드 handler.py 기준: event_name은 "llm"
        if (evt.event !== "llm") return

        const data = evt.data || {}
        const t = data.type

        // 0) 잘못된 입력 안내(배열일 수도 있음)
        if (t === "error_messages") {
          const msgs = Array.isArray(data.content) ? data.content : []
          if (msgs.length) {
            gotAnyAssistantContentRef.current = true
            appendAssistantText(chatId, turnId, msgs.join("\n") + "\n")
          } else if (typeof data.content === "string" && data.content.trim()) {
            gotAnyAssistantContentRef.current = true
            appendAssistantText(chatId, turnId, data.content.trim() + "\n")
          }
          return
        }

        // 1) 안내 멘트(추가질문 시작 멘트)
        if (t === "qna_ment") {
          const ment = (data.content ?? "").toString()
          if (ment.trim()) {
            gotAnyAssistantContentRef.current = true
            appendAssistantText(chatId, turnId, ment.trim() + "\n")
          }
          return
        }

        // 2) 추가질문 리스트
        if (t === "addition_questions") {
          const qs: string[] = Array.isArray(data.questions) ? data.questions : []
          if (qs.length > 0) {
            // 멘트가 직전에 왔을 수도 있으니, 여기서는 멘트를 따로 저장하지 않고 블록만 출력
            pendingClarifyRef.current = { originalQuestion: params.question, questions: qs, answers: [] }

            if (!gotAnyAssistantContentRef.current) {
              // qna_ment가 먼저 안 왔어도, 여기서 최소 안내문 출력
              appendAssistantText(chatId, turnId, formatClarifyBlock(null, qs))
            } else {
              // 이미 멘트가 찍혔다면 질문만 이어붙이기
              appendAssistantText(chatId, turnId, "\n" + qs.map((q, i) => `${i + 1}) ${q}`).join("\n"))
            }
            gotAnyAssistantContentRef.current = true
          }
          return
        }

        // 3) 최종 질문(디버그 표시용)
        if (t === "final_question") {
          const fq = (data.question ?? "").toString().trim()
          if (DEBUG_SHOW_INTERNAL && fq) {
            appendAssistantText(chatId, turnId, `최종 검색어 : ${fq}`)
          }
          // final_question을 받았다는 건 추가질문 단계 종료로 볼 수 있음
          pendingClarifyRef.current = null
          return
        }
      })
    } catch (e: any) {
      statusStickyRef.current = true
      setAssistantStatus(chatId, turnId, `스트림 처리 실패: ${e?.message ?? String(e)}`)
      releaseSendLock()
    } finally {
      if (!ended) releaseSendLock()
    }
  }

  async function handleSend(text: string, agent: Agent) {
    if (!chat) return
    if (sendLockRef.current) return

    const trimmed = (text ?? "").trim()
    if (!trimmed) return

    sendLockRef.current = true
    statusStickyRef.current = false
    gotAnyAssistantContentRef.current = false
    setIsLoading(true)

    addUserMessage(chat.id, trimmed)

    const turnId = newId()
    ensureAssistantMessage(chat.id, turnId, "질문분석중...")

    const latestMessages = getLatestMessagesFor(chat.id)
    const pending = pendingClarifyRef.current

    // ✅ 추가질문 답변 수집 모드
    if (pending && pending.questions.length) {
      const nextAnswers = [...pending.answers, trimmed]
      const needCount = pending.questions.length

      // 아직 답변이 덜 모였으면: 백엔드 호출하지 않고 "다음 질문"만 프론트에서 안내
      if (nextAnswers.length < needCount) {
        pendingClarifyRef.current = { ...pending, answers: nextAnswers }

        const nextQ = pending.questions[nextAnswers.length] // 0-based
        // UI 변경 없이: assistant 메시지에 다음 질문 한 줄만 이어서 표시
        appendAssistantText(chat.id, turnId, `${nextAnswers.length + 1}) ${nextQ}\n`)
        releaseSendLock()
        return
      }

      // 답변이 모두 모이면: 그때 백엔드에 한 번에 전달
      pendingClarifyRef.current = null
      await startStream(chat.id, turnId, {
        question: pending.originalQuestion,
        messages: latestMessages,
        clarifying_questions: pending.questions,
        clarifying_answers: nextAnswers,
      })
      return
    }

    // ✅ 일반 질문(첫 진입)
    await startStream(chat.id, turnId, {
      question: trimmed,
      messages: latestMessages,
      clarifying_questions: [],
      clarifying_answers: [],
    })
  }

  // 홈에서 넘어온 q= 자동 실행 유지
  const autoRanRef = useRef(false)
  useEffect(() => {
    if (!chat) return
    if (!qFromUrl) return
    if (autoRanRef.current) return
    autoRanRef.current = true

    router.replace(`/chat/${id}`)
    handleSend(qFromUrl, chat.agent)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat, qFromUrl, id])

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
              setChats((prev) => prev.map((c) => (c.id === chat.id ? { ...c, agent: a, updatedAt: now() } : c)))
            }}
            onSend={(t) => handleSend(t, chat.agent)}
          />
        </div>
      </div>
    </div>
  )
}
