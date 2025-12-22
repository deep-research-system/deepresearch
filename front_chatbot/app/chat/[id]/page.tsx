"use client"

import { useMemo, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { useChat } from "@/components/chat-provider"
import type { Agent } from "@/lib/chat-store"
import { readSseStream } from "@/lib/sse"

// 이벤트를 받아서 메시지로 바꾸는 페이지지


export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { chats, setChats, toggleSidebar } = useChat()
  const [isLoading, setIsLoading] = useState(false)
  const lastAutoInvokeMessageId = useRef<string | null>(null)


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

  const API_URL = "http://localhost:8000/invoke/stream"

  const appendAssistant = (content: string) => {
    const assistantMessage = {
      id: crypto.randomUUID(),
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



  const pushUserMessage = (content: string) => {
    const userMsg = {
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

  const startStream = async (question: string) => {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        messages: chat.messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        clarifying_questions: [],
        clarifying_answers: [],
      }),
    })
  
    if (!res.ok) {
      appendAssistant(`서버 오류 (HTTP ${res.status})`)
      return
    }
  
    await readSseStream(res, (evt) => {
      switch (evt.event) {
        case "start":
          appendAssistant(evt.data?.message ?? "리서치 시작")
          break
  
        case "node_update":
          // UX 개선은 다음 단계에서
          appendAssistant(evt.data?.message ?? `[${evt.data?.node}] 진행 중`)
          break
  
        case "assistant":
          if (evt.data?.content) {
            appendAssistant(evt.data.content)
          }
          break
  
        case "error":
          appendAssistant(`오류: ${evt.data?.message ?? "알 수 없는 오류"}`)
          break
  
        case "end":
          appendAssistant(evt.data?.message ?? "리서치 종료")
          break
      }
    })
  }


  const handleSend = async (message: string) => {
    pushUserMessage(message)
    setIsLoading(true)
  
    try {
      await startStream(message)
    } catch (e) {
      console.error("SSE 오류:", e)
      appendAssistant("스트리밍 중 오류가 발생했습니다.")
    } finally {
      setIsLoading(false)
    }
  }


  const handleAgentChange = (agent: Agent) => {
    setChats((prev) =>
      prev.map((c) => (c.id === id ? { ...c, agent, updatedAt: Date.now() } : c)),
    )
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
