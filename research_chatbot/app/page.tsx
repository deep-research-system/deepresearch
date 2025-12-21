"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useChat } from "@/components/chat-provider"
import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { createChat, type Agent } from "@/lib/chat-store"

export default function HomePage() {
  const [agent, setAgent] = useState<Agent>("General")
  const router = useRouter()
  const { toggleSidebar, setChats } = useChat()

  const API_URL = "http://localhost:8000/invoke"

  const extractAssistantContent = (data: any): string => {
    if (!data) return "응답 완료!"

    if (typeof data.final_answer === "string" && data.final_answer.trim()) {
      return data.final_answer
    }
    if (typeof data.report_markdown === "string" && data.report_markdown.trim()) {
      return data.report_markdown
    }

    if (Array.isArray(data.messages)) {
      const lastAssistant = [...data.messages].reverse().find((m) => m?.role === "assistant")
      if (lastAssistant?.content) return lastAssistant.content
    }

    return "응답 완료!"
  }

  const handleSend = async (message: string) => {
    const newChat = createChat(agent)

    const userMessage = {
      id: `msg-${Date.now()}`,
      role: "user" as const,
      content: message,
      createdAt: Date.now(),
    }

    newChat.messages.push(userMessage)
    newChat.title = message.slice(0, 50) + (message.length > 50 ? "..." : "")
    newChat.updatedAt = Date.now()

    // 1) 먼저 채팅을 스토어에 등록하고 이동
    setChats((prev) => [...prev, newChat])
    router.push(`/chat/${newChat.id}`)

    // 2) 서버 호출
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: message,
          active_mode: agent === "General" ? "chat" : "research",
          messages: newChat.messages.map((m) => ({ role: m.role, content: m.content })),
          // 백엔드 확장 스키마에 맞춰 항상 포함(없으면 빈 배열)
          clarifying_questions: [],
          clarifying_answers: [],
        }),
      })

      const result = await response.json()

      if (!result?.success || !result?.data) {
        throw new Error("Invalid response shape")
      }

      const data = result.data

      // (A) 딥리서치 추가질문 단계가 시작되면: /chat/[id] 페이지에서 처리하는 게 정석이지만,
      // 새 채팅 시작에서도 최소한 안내 메시지는 남겨둔다.
      if (data.need_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
        const qText =
          "추가로 몇 가지 확인할게요.\n" +
          data.clarifying_questions.map((q: string, i: number) => `${i + 1}) ${q}`).join("\n")

        const assistantMessage = {
          id: `msg-${Date.now()}`,
          role: "assistant" as const,
          content: qText,
          createdAt: Date.now(),
        }

        setChats((prev) =>
          prev.map((chat) =>
            chat.id === newChat.id
              ? { ...chat, messages: [...chat.messages, assistantMessage], updatedAt: Date.now() }
              : chat,
          ),
        )
        return
      }

      const assistantMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant" as const,
        content: extractAssistantContent(data),
        createdAt: Date.now(),
      }

      setChats((prev) =>
        prev.map((chat) =>
          chat.id === newChat.id
            ? { ...chat, messages: [...chat.messages, assistantMessage], updatedAt: Date.now() }
            : chat,
        ),
      )
    } catch (error) {
      console.error("Invoke 오류:", error)
      const assistantMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant" as const,
        content: "죄송합니다. 서버 연결 오류가 발생했습니다.",
        createdAt: Date.now(),
      }
      setChats((prev) =>
        prev.map((chat) =>
          chat.id === newChat.id
            ? { ...chat, messages: [...chat.messages, assistantMessage], updatedAt: Date.now() }
            : chat,
        ),
      )
    }
  }

  return (
    <>
      <ChatHeader title="New Chat" onMenuClick={toggleSidebar} />
      <MessageList messages={[]} />
      <ChatInput onSend={handleSend} agent={agent} onAgentChange={setAgent} />
    </>
  )
}
