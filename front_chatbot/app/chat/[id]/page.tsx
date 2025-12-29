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

// “반드시 순차 출력”을 위한 고정 딜레이 (원하면 80~200 사이로 조절)
const LINE_DELAY_MS = 100

function now() {
  return Date.now()
}
function newId() {
  return crypto.randomUUID()
}
function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
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

  // 출력 큐: “화면에 찍는 텍스트”는 무조건 이 큐를 통해 순차 처리
  const printChainRef = useRef<Promise<void>>(Promise.resolve())

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

  // ✅ “순차 출력 보장” 함수: 반드시 이걸로만 출력
  function enqueuePrint(chatId: string, turnId: string, line: string, delayMs = LINE_DELAY_MS) {
    printChainRef.current = printChainRef.current.then(async () => {
      appendAssistantText(chatId, turnId, line)
      await sleep(delayMs)
    })
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

        // 백엔드 handler.py 기준: event_name은 "llm"
        if (evt.event !== "llm") return

        const data = evt.data || {}
        const t = data.type

        // 0) 잘못된 입력 안내
        if (t === "error_messages") {
          // content가 문자열/배열 어떤 형태든 “줄 단위”로 순차 출력
          if (Array.isArray(data.content)) {
            for (const msg of data.content) {
              if (typeof msg === "string" && msg.trim()) {
                enqueuePrint(chatId, turnId, msg.trim() + "\n")
              }
            }
          } else if (typeof data.content === "string" && data.content.trim()) {
            enqueuePrint(chatId, turnId, data.content.trim() + "\n")
          }
          return
        }

        // 1) 안내 멘트(추가질문 시작 멘트) — 반드시 1줄 먼저 출력되게 큐에 태움
        if (t === "qna_ment") {
          const ment = (data.content ?? "").toString()
          if (ment.trim()) {
            enqueuePrint(chatId, turnId, ment.trim() + "\n")
          }
          return
        }

        // 2) 추가질문 — 백엔드가 “한 개씩” 보내는 전제:
        //    {"type":"addition_questions","questions":"질문1"} 가 여러 번 옴
        if (t === "addition_questions") {
          const q = data.questions
          if (typeof q === "string" && q.trim()) {
            // pending이 아직 없으면 생성
            if (!pendingClarifyRef.current) {
              pendingClarifyRef.current = {
                originalQuestion: params.question,
                questions: [],
                answers: [],
              }
            }

            // 질문 누적
            pendingClarifyRef.current.questions.push(q.trim())
            const idx = pendingClarifyRef.current.questions.length

            // ✅ “질문 1개씩” 반드시 순차 출력 (큐 + 딜레이)
            enqueuePrint(chatId, turnId, `${idx}) ${q.trim()}\n`)
          }
          return
        }

        // 3) 최종 질문(표시용) — 이것도 큐로 출력(원하면)
        if (t === "final_question") {
          const fq = (data.question ?? "").toString().trim()
          if (DEBUG_SHOW_INTERNAL && fq) {
            enqueuePrint(chatId, turnId, `최종 검색어 : ${fq}\n`, 0)
          }
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
    setIsLoading(true)

    addUserMessage(chat.id, trimmed)

    const turnId = newId()
    ensureAssistantMessage(chat.id, turnId, "질문분석중...")

    const latestMessages = getLatestMessagesFor(chat.id)
    const pending = pendingClarifyRef.current

    // 추가질문 답변 수집 모드 (pending.questions 길이만큼 답을 모아서 한 번에 전송)
    if (pending && pending.questions.length) {
      const nextAnswers = [...pending.answers, trimmed]
      const needCount = pending.questions.length

      // 아직 답변이 덜 모였으면: 다음 질문을 화면에만 안내(백엔드 호출 X)
      if (nextAnswers.length < needCount) {
        pendingClarifyRef.current = { ...pending, answers: nextAnswers }

        const nextQ = pending.questions[nextAnswers.length] // 0-based
        // 사용자에게 다음 질문을 “순차 출력”으로 표시 (선택)
        enqueuePrint(chat.id, turnId, `${nextAnswers.length + 1}) ${nextQ}\n`)
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

    // 일반 질문(첫 진입)
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
