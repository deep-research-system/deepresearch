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
  questions: string[] // addition_questions
}

const DEBUG_SHOW_INTERNAL = true
const API_URL = "http://localhost:8000/deepresearch"

// “반드시 순차 출력”을 위한 고정 딜레이
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

  const subqCountRef = useRef<Record<string, number>>({})
  const pendingClarifyRef = useRef<PendingClarify | null>(null)
  const sendLockRef = useRef(false)
  const statusStickyRef = useRef(false)
  const searchCountRef = useRef<Record<string, number>>({})

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

  // “순차 출력 보장”
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

  async function startStream(chatId: string, turnId: string, params: any) {
    console.log("[REQ_BODY]", params)
    
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

        // 백엔드 handler 기준: event_name은 "llm"
        if (evt.event !== "llm") return

        const data = evt.data || {}
        const t = data.type

        // 0) 잘못된 입력 안내
        if (t === "error_messages") {
          if (Array.isArray(data.content)) {
            for (const msg of data.content) {
              if (typeof msg === "string" && msg.trim()) enqueuePrint(chatId, turnId, msg.trim() + "\n")
            }
          } else if (typeof data.content === "string" && data.content.trim()) {
            enqueuePrint(chatId, turnId, data.content.trim() + "\n")
          }
          return
        }

        // 1) 안내 멘트
        if (t === "qna_ment") {
          const ment = (data.content ?? "").toString()
          if (ment.trim()) enqueuePrint(chatId, turnId, ment.trim() + "\n")
          return
        }

        // 2) 추가질문 (서버가 한 개씩 보내는 전제)
        // {"type":"addition_questions","questions":"질문1"} 가 여러 번 옴
        if (t === "addition_questions") {
          const q = data.questions
          if (typeof q === "string" && q.trim()) {
            // pending이 아직 없으면 생성
            if (!pendingClarifyRef.current) {
              // IMPORTANT: "원 질문"은 1차 요청 params.question 기준으로 저장
              pendingClarifyRef.current = {
                originalQuestion: params.question,
                questions: [],
              }
            }

            pendingClarifyRef.current.questions.push(q.trim())
            const idx = pendingClarifyRef.current.questions.length

            // 순차 출력
            enqueuePrint(chatId, turnId, `${idx}) ${q.trim()}\n`)
          }
          return
        }

        // 3) 최종 질문
        if (t === "final_question") {
          const fq = (data.question ?? "").toString().trim()
          if (DEBUG_SHOW_INTERNAL && fq) {
            enqueuePrint(chatId, turnId, `최종 검색어 : ${fq}\n`, 0)
          }
          // 최종 확정이면 pending 종료
          pendingClarifyRef.current = null
          return
        }

        // 4) 서브쿼리
        if (t === "subqueries") {
          const q = (data.query ?? "").toString().trim()
          if (q) {
            // turnId별 번호 증가
            if (subqCountRef.current[turnId] == null) subqCountRef.current[turnId] = 0
            subqCountRef.current[turnId] += 1
        
            // 순차 출력 (1) ... 2) ... 형태
            enqueuePrint(chatId, turnId, `${subqCountRef.current[turnId]}) ${q}\n`)
          }
          return
        }

        // 5) 검색 결과 1건 (URL)
        if (t === "search_results") {
          const r = (data.result && typeof data.result === "object") ? data.result : data
          const title = (r.title ?? "").toString().trim()
          const url = (r.url ?? "").toString().trim()
          console.log("[SEARCH_PAYLOAD]", { title, url, raw: data })

          if (url) {
            // turnId별 번호 증가
            if (searchCountRef.current[turnId] == null) searchCountRef.current[turnId] = 0
            searchCountRef.current[turnId] += 1

            const idx = searchCountRef.current[turnId]
      
            // 클릭 가능한 링크: HTML 문자열로 출력
            // (MessageList가 HTML 렌더링을 지원하지 않으면 아래 "대안" 참고)
            const label = title || url
            enqueuePrint(chatId, turnId, `${idx}) [${label}](${url})\n`)}
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
    subqCountRef.current[turnId] = 0
    ensureAssistantMessage(chat.id, turnId, "질문분석중...")

    const pending = pendingClarifyRef.current

    // ===== 2차 요청 모드: 추가질문이 떠있는 상태에서 사용자 입력이 들어온 경우 =====
    if (pending && pending.questions.length) {
      // 너 의도: 3개 질문 중 1개만 답해도 서버가 판단하고, 부족하면 재질문 다시 내려줌
      // 따라서 "한 번 입력될 때마다" 바로 2차 요청을 보낸다.
      pendingClarifyRef.current = null

      await startStream(chat.id, turnId, {
        question: pending.originalQuestion,                 // 원 질문
        addition_questions: pending.questions,              // 추가질문 리스트
        addition_questions_answers: [trimmed],              // 사용자 답변 (1개여도 리스트)
      })
      return
    }

    // ===== 1차 요청 모드 =====
    await startStream(chat.id, turnId, {
      question: trimmed,
      addition_questions: null,
      addition_questions_answers: null,
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
