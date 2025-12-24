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

  const handleSend = async (message: string) => {
    const trimmed = (message ?? "").trim()
    if (!trimmed) return

    const newChat = createChat(agent)
    newChat.title = trimmed.slice(0, 50) + (trimmed.length > 50 ? "..." : "")
    newChat.updatedAt = Date.now()

    // 1) 스토어 등록
    setChats((prev) => [...prev, newChat])

    // 2) 첫 질문을 pending으로 저장 (chat/[id]에서 자동 전송)
    try {
      localStorage.setItem(`pending-message-${newChat.id}`, trimmed)
    } catch {
      // localStorage 접근 불가 환경이면 자동전송이 안 될 수 있음
    }

    // 3) 이동
    router.push(`/chat/${newChat.id}`)
  }

  return (
    <>
      <ChatHeader title="New Chat" onMenuClick={toggleSidebar} />
      <MessageList messages={[]} />
      <ChatInput onSend={handleSend} agent={agent} onAgentChange={setAgent} />
    </>
  )
}
