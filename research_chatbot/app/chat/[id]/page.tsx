"use client"

import { useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { useChat } from "@/components/chat-provider"
import type { Agent } from "@/lib/chat-store"

type ClarifyState = {
  originalQuestion: string
  questions: string[]
}

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { chats, setChats, toggleSidebar } = useChat()
  const [isLoading, setIsLoading] = useState(false)

  // DeepResearch 추가질문 단계 상태
  const [pendingClarify, setPendingClarify] = useState<ClarifyState | null>(null)
  const [clarifyAnswers, setClarifyAnswers] = useState<string[]>([])

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

  const API_URL = "http://localhost:8000/invoke"

  const appendAssistant = (content: string) => {
    const assistantMessage = {
      id: `msg-${Date.now()}`,
      role: "assistant" as const,
      content,
      createdAt: Date.now(),
    }

    setChats((prev) =>
      prev.map((c) =>
        c.id === id
          ? { ...c, messages: [...c.messages, assistantMessage], updatedAt: Date.now() }
          : c,
      ),
    )
  }

  const handleSend = async (message: string) => {
    // (A) 지금이 추가질문 답변을 받는 단계라면: 여기서는 ChatInput으로 메시지 보내는 걸 막는 게 정석
    //     답변 제출은 별도 폼(handleSubmitClarify)로만 처리합니다.
    if (pendingClarify) return

    const userMsg = {
      id: `msg-${Date.now()}`,
      role: "user" as const,
      content: message,
      createdAt: Date.now(),
    }

    // Optimistic update
    setChats((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              messages: [...c.messages, userMsg],
              title:
                c.title === "New Chat"
                  ? message.slice(0, 50) + (message.length > 50 ? "..." : "")
                  : c.title,
              updatedAt: Date.now(),
            }
          : c,
      ),
    )

    setIsLoading(true)
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: message,
          active_mode: chat.agent === "General" ? "chat" : "research",
          messages: chat.messages.concat([userMsg]).map((m) => ({
            role: m.role,
            content: m.content,
          })),
          clarifying_questions: [],
          clarifying_answers: [],
        }),
      })

      const result = await response.json()

      if (!result?.success || !result?.data) {
        appendAssistant("죄송합니다. 서버 응답이 올바르지 않습니다.")
        return
      }

      const data = result.data

      // (1) DeepResearch + 추가질문 필요
      if (data.need_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
        setPendingClarify({
          originalQuestion: message,
          questions: data.clarifying_questions,
        })
        setClarifyAnswers(new Array(data.clarifying_questions.length).fill(""))

        // 사용자에게 추가 질문을 채팅으로도 보여줌
        const qText =
          "추가로 몇 가지 확인할게요.\n" +
          data.clarifying_questions.map((q: string, i: number) => `${i + 1}) ${q}`).join("\n")
        appendAssistant(qText)
        return
      }

      // (2) 일반 응답 / 딥리서치 최종 보고서
      const content =
        data.final_answer ||
        data.report_markdown ||
        // messages는 리스트일 수 있으니 "마지막 assistant"를 우선 탐색
        (Array.isArray(data.messages)
          ? [...data.messages].reverse().find((m: any) => m?.role === "assistant")?.content
          : null) ||
        "응답 완료!"

      appendAssistant(content)
    } catch (error) {
      console.error("Invoke 오류:", error)
      appendAssistant("죄송합니다. 서버 연결 오류가 발생했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  // (B) 추가질문 답변 제출 → 2차 invoke
  const handleSubmitClarify = async () => {
    if (!pendingClarify) return

    // 빈 답변 방지(최소한 모두 입력)
    if (clarifyAnswers.some((a) => !a.trim())) {
      appendAssistant("추가 질문 답변을 모두 입력해 주세요.")
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: pendingClarify.originalQuestion,
          active_mode: "research",
          messages: chat.messages.map((m) => ({ role: m.role, content: m.content })),
          clarifying_questions: pendingClarify.questions,
          clarifying_answers: clarifyAnswers,
        }),
      })

      const result = await response.json()
      if (!result?.success || !result?.data) {
        appendAssistant("죄송합니다. 서버 응답이 올바르지 않습니다.")
        return
      }

      const data = result.data
      const content =
        data.report_markdown ||
        data.final_answer ||
        (Array.isArray(data.messages)
          ? [...data.messages].reverse().find((m: any) => m?.role === "assistant")?.content
          : null) ||
        "보고서 생성 완료!"

      // 추가질문 단계 종료
      setPendingClarify(null)
      setClarifyAnswers([])

      appendAssistant(content)
    } catch (error) {
      console.error("Clarify invoke 오류:", error)
      appendAssistant("죄송합니다. 추가 질문 처리 중 오류가 발생했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleAgentChange = (agent: Agent) => {
    setChats((prev) =>
      prev.map((c) => (c.id === id ? { ...c, agent, updatedAt: Date.now() } : c)),
    )
    // 모드 변경 시, 진행 중이던 추가질문 세션은 정리(혼동 방지)
    setPendingClarify(null)
    setClarifyAnswers([])
  }

  return (
    <>
      <ChatHeader title={chat.title} onMenuClick={toggleSidebar} />
      <MessageList messages={chat.messages} />

      {/* 추가질문 입력 UI (DeepResearch 전용) */}
      {pendingClarify && (
        <div className="px-4 pb-3">
          <div className="rounded-lg border p-3 space-y-2">
            <div className="text-sm font-medium">추가 질문 답변</div>
            {pendingClarify.questions.map((q, idx) => (
              <div key={idx} className="space-y-1">
                <div className="text-sm">{idx + 1}) {q}</div>
                <input
                  className="w-full rounded-md border px-3 py-2 text-sm"
                  value={clarifyAnswers[idx] ?? ""}
                  onChange={(e) => {
                    const v = e.target.value
                    setClarifyAnswers((prev) => {
                      const next = [...prev]
                      next[idx] = v
                      return next
                    })
                  }}
                  placeholder="답변을 입력하세요"
                />
              </div>
            ))}

            <button
              className="mt-2 inline-flex items-center rounded-md border px-3 py-2 text-sm"
              onClick={handleSubmitClarify}
              disabled={isLoading}
            >
              답변 제출 후 보고서 생성
            </button>
          </div>
        </div>
      )}

      <ChatInput
        onSend={handleSend}
        disabled={isLoading || !!pendingClarify}
        agent={chat.agent}
        onAgentChange={handleAgentChange}
      />
    </>
  )
}
