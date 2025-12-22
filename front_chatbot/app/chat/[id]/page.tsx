"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { useChat } from "@/components/chat-provider"
import type { Agent } from "@/lib/chat-store"

type ClarifyState = {
  originalQuestion: string
  questions: string[]
  index: number
}

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { chats, setChats, toggleSidebar } = useChat()
  const [isLoading, setIsLoading] = useState(false)
  const lastAutoInvokeMessageId = useRef<string | null>(null)

  const [pendingClarify, setPendingClarify] = useState<ClarifyState | null>(null)
  const [clarifyAnswers, setClarifyAnswers] = useState<string[]>([])

  const chat = useMemo(() => chats.find((c) => c.id === id), [chats, id])

  if (!chat) {
    return (
      <>
        <ChatHeader title="Chat not found" onMenuClick={toggleSidebar} />
        <div className="flex-1 flex items-center justify-center">
          <button className="underline" onClick={() => router.push("/")}>홈으로 이동</button>
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

  const invokeBackend = async (opts: {
    question: string
    mode: "chat" | "research"
    messages: { role: string; content: string }[]
    clarifying_questions?: string[]
    clarifying_answers?: string[]
  }) => {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: opts.question,
        active_mode: opts.mode,
        messages: opts.messages,
        clarifying_questions: opts.clarifying_questions ?? [],
        clarifying_answers: opts.clarifying_answers ?? [],
      }),
    })
    return await response.json()
  }

  const pushUserMessage = (content: string) => {
    const userMsg = {
      id: `msg-${Date.now()}`,
      role: "user" as const,
      content,
      createdAt: Date.now(),
    }

    setChats((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              messages: [...c.messages, userMsg],
              title:
                c.title === "New Chat"
                  ? content.slice(0, 50) + (content.length > 50 ? "..." : "")
                  : c.title,
              updatedAt: Date.now(),
            }
          : c,
      ),
    )

    return userMsg
  }

  const handleSend = async (message: string) => {
    const userMsg = pushUserMessage(message)

    if (pendingClarify) {
      const idx = pendingClarify.index
      const nextAnswers = [...clarifyAnswers]
      nextAnswers[idx] = message
      setClarifyAnswers(nextAnswers)

      const isLast = idx >= pendingClarify.questions.length - 1
      if (!isLast) {
        const nextIdx = idx + 1
        setPendingClarify({ ...pendingClarify, index: nextIdx })
        appendAssistant(`${nextIdx + 1}) ${pendingClarify.questions[nextIdx]}`)
        return
      }

      setIsLoading(true)
      try {
        const result = await invokeBackend({
          question: pendingClarify.originalQuestion,
          mode: "research",
          messages: chat.messages.concat([userMsg]).map((m) => ({ role: m.role, content: m.content })),
          clarifying_questions: pendingClarify.questions,
          clarifying_answers: nextAnswers,
        })

        if (!result?.success || !result?.data) {
          appendAssistant("죄송합니다. 서버 응답이 올바르지 않습니다.")
          return
        }

        const data = result.data
        const content =
          data.final_answer ||
          data.final_question ||
          data.report_markdown ||
          (Array.isArray(data.messages)
            ? [...data.messages].reverse().find((m: any) => m?.role === "assistant")?.content
            : null) ||
          "완료!"

        setPendingClarify(null)
        setClarifyAnswers([])
        appendAssistant(content)
      } catch (e) {
        console.error("Clarify invoke 오류:", e)
        appendAssistant("죄송합니다. 추가 질문 처리 중 오류가 발생했습니다.")
      } finally {
        setIsLoading(false)
      }
      return
    }

    setIsLoading(true)
    try {
      const result = await invokeBackend({
        question: message,
        mode: "research",
        messages: chat.messages.concat([userMsg]).map((m) => ({ role: m.role, content: m.content })),
      })

      if (!result?.success || !result?.data) {
        appendAssistant("죄송합니다. 서버 응답이 올바르지 않습니다.")
        return
      }

      const data = result.data

      if (data.need_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
        setPendingClarify({
          originalQuestion: message,
          questions: data.clarifying_questions,
          index: 0,
        })
        setClarifyAnswers(new Array(data.clarifying_questions.length).fill(""))
        appendAssistant("추가로 몇 가지 확인할게요.")
        appendAssistant(`1) ${data.clarifying_questions[0]}`)
        return
      }

      const content =
        data.final_answer ||
        data.report_markdown ||
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

  useEffect(() => {
    if (!chat) return
    if (isLoading) return
    if (pendingClarify) return

    const last = chat.messages.at(-1)
    if (!last || last.role !== "user") return
    if (lastAutoInvokeMessageId.current === last.id) return

    const hasAnyAssistant = chat.messages.some((m) => m.role === "assistant")
    if (hasAnyAssistant) return

    lastAutoInvokeMessageId.current = last.id
    ;(async () => {
      setIsLoading(true)
      try {
        const result = await invokeBackend({
          question: last.content,
          mode: "research",
          messages: chat.messages.map((m) => ({ role: m.role, content: m.content })),
        })

        if (!result?.success || !result?.data) {
          appendAssistant("죄송합니다. 서버 응답이 올바르지 않습니다.")
          return
        }

        const data = result.data

        if (data.need_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
          setPendingClarify({
            originalQuestion: last.content,
            questions: data.clarifying_questions,
            index: 0,
          })
          setClarifyAnswers(new Array(data.clarifying_questions.length).fill(""))
          appendAssistant("추가로 몇 가지 확인할게요.")
          appendAssistant(`1) ${data.clarifying_questions[0]}`)
          return
        }

        const content =
          data.final_answer ||
          data.report_markdown ||
          (Array.isArray(data.messages)
            ? [...data.messages].reverse().find((m: any) => m?.role === "assistant")?.content
            : null) ||
          "응답 완료!"

        appendAssistant(content)
      } catch (e) {
        console.error("Auto invoke 오류:", e)
        appendAssistant("죄송합니다. 서버 연결 오류가 발생했습니다.")
      } finally {
        setIsLoading(false)
      }
    })()
  }, [chat, isLoading, pendingClarify])

  const handleAgentChange = (agent: Agent) => {
    setChats((prev) =>
      prev.map((c) => (c.id === id ? { ...c, agent, updatedAt: Date.now() } : c)),
    )
    setPendingClarify(null)
    setClarifyAnswers([])
  }

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
