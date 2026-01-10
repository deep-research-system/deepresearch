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

const API_URL = "http://localhost:8000/deepresearch"
const LINE_DELAY_MS = 80

function now() {
  return Date.now()
}
function newId() {
  return crypto.randomUUID()
}
function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

type Bucket = "final" | "subq" | "sources" | "summary"  | "report"

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

  // 카운터(턴 단위)
  const subqCountRef = useRef<Record<string, number>>({})
  const sourcesCountRef = useRef<Record<string, number>>({})
  const summaryCountRef = useRef<Record<string, number>>({})

  // 버킷(버블) 초기화 여부: 헤더 1회 출력용
  const bucketInitRef = useRef<Record<string, boolean>>({})

  // 출력 큐(무조건 순차 출력)
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

  // 줄 단위 순차 출력(큐 보장)
  function enqueuePrint(chatId: string, turnId: string, text: string, delayMs = LINE_DELAY_MS) {
    printChainRef.current = printChainRef.current.then(async () => {
      appendAssistantText(chatId, turnId, text)
      await sleep(delayMs)
    })
  }

  function enqueueLines(chatId: string, turnId: string, lines: string[], delayMs = LINE_DELAY_MS) {
    for (const line of lines) {
      enqueuePrint(chatId, turnId, line + "\n", delayMs)
    }
  }

  function addUserMessage(chatId: string, content: string) {
    updateChatMessages(chatId, (prev) => [...prev, { id: newId(), role: "user", content, createdAt: now() }])
  }

  function releaseSendLock() {
    sendLockRef.current = false
    setIsLoading(false)
  }

  // ===== 버킷(별도 버블) 유틸 =====
  function bucketTurnId(baseTurnId: string, bucket: Bucket) {
    return `${baseTurnId}:${bucket}`
  }

  function bucketHeader(bucket: Bucket) {
    if (bucket === "final") return "최종 검색어"
    if (bucket === "subq") return "서브쿼리"
    if (bucket === "sources") return "출처(URL)"
    if (bucket === "summary") return "문서 요약"
    return "최종 보고서"
  }

  function ensureBucket(chatId: string, baseTurnId: string, bucket: Bucket) {
    const bId = bucketTurnId(baseTurnId, bucket)
    const key = `${chatId}|${bId}`
    if (!bucketInitRef.current[key]) {
      ensureAssistantMessage(chatId, bId, "")
      enqueueLines(chatId, bId, [bucketHeader(bucket), "-----------------"], 0)
      bucketInitRef.current[key] = true
    }
    return bId
  }

  function setBucketStatus(chatId: string, baseTurnId: string, bucket: Bucket, text: string) {
    const bId = ensureBucket(chatId, baseTurnId, bucket)
    setAssistantStatus(chatId, bId, text)
  }

  // node_update 메시지를 어떤 버킷에 붙일지 결정(문구는 stream.py에서 온 그대로)
  function routeNodeUpdateToBucket(msg: string): Bucket | null {
    // stream.py 문구 기준으로 매칭 (원하면 더 촘촘하게 조정 가능)
    if (msg.includes("서브쿼리")) return "subq"
    if (msg.includes("검색")) return "sources"
    if (msg.includes("문서 요약") || msg.includes("요약")) return "summary"
    if (msg.includes("최종 보고서")) return "report"
    if (msg.includes("최종 질문") || msg.includes("최종 검색어") || msg.includes("확정")) return "final"

    // 그 외(질문 분석/추가 질문/답변 판정 등)는 기본 버블에서만 표시
    return null
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
        if (evt.event === "start") {
          setAssistantStatus(chatId, turnId, evt.data?.message ?? "시작")
          return
        }

        if (evt.event === "node_update") {
          const msg = (evt.data?.message ?? "").toString().trim()
          if (!msg) return

          // 기본 버블도 상태 갱신(원하면 유지)
          setAssistantStatus(chatId, turnId, msg)

          // 버킷별 statusText에도 동일 문구 표시
          const b = routeNodeUpdateToBucket(msg)
          if (b) setBucketStatus(chatId, turnId, b, msg)

          return
        }

        if (evt.event === "error") {
          statusStickyRef.current = true
          setAssistantStatus(chatId, turnId, `에러: ${evt.data?.message ?? "unknown"}`)
          // 에러는 전체 UX 상단에 고정하고 싶으면 여기서 버킷 상태도 같이 고정 가능
          releaseSendLock()
          return
        }

        if (evt.event === "end") {
          ended = true
          releaseSendLock()
          return
        }

        if (evt.event !== "llm") return

        const data = evt.data || {}
        const t = data.type

        // ===== (1) 기본 버블(turnId): 에러/추가질문/안내 =====
        if (t === "error_messages") {
          const c = data.content
          if (Array.isArray(c)) {
            const lines = c.filter((x: any) => typeof x === "string" && x.trim()).map((x: string) => x.trim())
            if (lines.length) enqueueLines(chatId, turnId, lines, 0)
          } else if (typeof c === "string" && c.trim()) {
            enqueueLines(chatId, turnId, [c.trim()], 0)
          }
          return
        }

        if (t === "qna_ment") {
          const ment = (data.content ?? "").toString().trim()
          if (ment) enqueueLines(chatId, turnId, [ment], 0)
          return
        }

        if (t === "addition_questions") {
          const q = (data.questions ?? "").toString().trim()
          if (!q) return

          if (!pendingClarifyRef.current) {
            pendingClarifyRef.current = {
              originalQuestion: params.question,
              questions: [],
            }
          }
          pendingClarifyRef.current.questions.push(q)
          const idx = pendingClarifyRef.current.questions.length
          enqueueLines(chatId, turnId, [`${idx}) ${q}`], 0)
          return
        }

        // ===== (2) 최종 검색어: final 버블 =====
        if (t === "final_question") {
          const fq = (data.question ?? "").toString().trim()
          if (!fq) return

          const bId = ensureBucket(chatId, turnId, "final")
          enqueueLines(chatId, bId, [fq], 0)

          pendingClarifyRef.current = null
          return
        }

        // ===== (3) 서브쿼리: subq 버블 =====
        if (t === "subqueries") {
          const q = (data.query ?? "").toString().trim()
          if (!q) return

          const bId = ensureBucket(chatId, turnId, "subq")

          if (subqCountRef.current[turnId] == null) subqCountRef.current[turnId] = 0
          subqCountRef.current[turnId] += 1
          const idx = subqCountRef.current[turnId]

          enqueueLines(chatId, bId, [`${idx}) ${q}`], 0)
          return
        }

        // ===== (4) URL(출처): sources 버블 =====
        // 요구사항: "제목" 한 줄 + "URL(클릭)" 한 줄로 출력
        if (t === "search_results") {
          const r = data.result && typeof data.result === "object" ? data.result : data
          const title = (r.title ?? "").toString().trim()
          const url = (r.url ?? "").toString().trim()
          if (!url) return

          const bId = ensureBucket(chatId, turnId, "sources")

          if (sourcesCountRef.current[turnId] == null) sourcesCountRef.current[turnId] = 0
          sourcesCountRef.current[turnId] += 1
          const idx = sourcesCountRef.current[turnId]

          const safeTitle = title || "(제목 없음)"
          // 1) 제목은 텍스트로
          // 2) URL은 화면에 URL 그대로 보이되 클릭 가능하게 (Markdown 링크)
          enqueueLines(chatId, bId, [`${idx}) ${safeTitle}`, `[${url}](${url})`], 0)
          return
        }

        // ===== (5) 문서 요약: summary 버블 하나에 문서별 섹션 누적(줄 단위) =====
        if (t === "doc_summary") {
          const doc = data.doc && typeof data.doc === "object" ? data.doc : null
          if (!doc) return

          const title = (doc.title ?? "").toString().trim()
          const url = (doc.url ?? "").toString().trim()
          const summary = (doc.summary ?? "").toString().trim()
          const bullets = Array.isArray(doc.bullets) ? doc.bullets : []
          const notes = (doc.reliability_notes ?? "").toString().trim()

          const bId = ensureBucket(chatId, turnId, "summary")

          if (summaryCountRef.current[turnId] == null) summaryCountRef.current[turnId] = 0
          summaryCountRef.current[turnId] += 1
          const idx = summaryCountRef.current[turnId]

          const lines: string[] = []
          lines.push("") // 섹션 분리
          lines.push(`[문서 ${idx}]`)

          if (url) {
            const label = title || url
            lines.push(`출처: [${label}](${url})`)
          } else if (title) {
            lines.push(`출처: ${title}`)
          }

          if (summary) {
            for (const sLine of summary.split("\n")) {
              if (sLine.trim()) lines.push(sLine.trim())
            }
          }

          if (bullets.length > 0) {
            for (const b of bullets) {
              if (typeof b === "string" && b.trim()) lines.push(`- ${b.trim()}`)
            }
          }

          if (notes) lines.push(`주의: ${notes}`)

          enqueueLines(chatId, bId, lines, 0)
          return
        }
        // ===== (6) 최종 보고서: report 버블 =====
        if (t === "final_report") {
          const report = (data.content ?? "").toString()
          if (!report.trim()) return
        
          const bId = ensureBucket(chatId, turnId, "report")
          // 보고서는 줄 단위로 나누지 말고 통째로 넣는 것이 Markdown 렌더링에 유리
          enqueuePrint(chatId, bId, report + "\n", 0)
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
    sourcesCountRef.current[turnId] = 0
    summaryCountRef.current[turnId] = 0

    // 기본 assistant 버블(질문 분석/추가질문/에러용)
    ensureAssistantMessage(chat.id, turnId, "질문분석중...")

    const pending = pendingClarifyRef.current

    // 2차 요청(추가질문 답변)
    if (pending && pending.questions.length) {
      pendingClarifyRef.current = null
      await startStream(chat.id, turnId, {
        question: pending.originalQuestion,
        addition_questions: pending.questions,
        addition_questions_answers: [trimmed],
      })
      return
    }

    // 1차 요청
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
