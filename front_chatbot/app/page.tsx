"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useChat } from "@/components/chat-provider"
import { ChatHeader } from "@/components/chat-header"
import { MessageList } from "@/components/message-list"
import { ChatInput } from "@/components/chat-input"
import { createChat, type Agent } from "@/lib/chat-store"

// 새채팅 생성/이동 페이지


export default function HomePage() {
  const [agent, setAgent] = useState<Agent>("General")
  const router = useRouter()
  const { toggleSidebar, setChats } = useChat()

  const handleSend = async (message: string) => {
    const newChat = createChat(agent)
    const userMessage = {
      id: crypto.randomUUID(),
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
  }
  return (
    <>
      <ChatHeader title="New Chat" onMenuClick={toggleSidebar} />
      <MessageList messages={[]} />
      <ChatInput onSend={handleSend} agent={agent} onAgentChange={setAgent} />
    </>
  )
}
