"use client"

import React, { useMemo, useState } from "react"
import { useParams, usePathname, useRouter } from "next/navigation"

import { Sidebar } from "@/components/sidebar"
import { useChat } from "@/components/chat-provider"
import { createChat } from "@/lib/chat-store"

export function ChatLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const params = useParams<{ id?: string }>()
  const { chats, setChats, clearAllChats, toggleSidebar } = useChat() as any

  const [sidebarOpen, setSidebarOpen] = useState(true)

  const activeChatId = useMemo(() => {
    // /chat/[id] 형태면 params.id가 존재
    const id = (params as any)?.id
    return typeof id === "string" ? id : null
  }, [params])

  const onClose = () => setSidebarOpen(false)

  const onNewChat = () => {
    const c = createChat("DeepResearch")

    // 1) state에 채팅 추가
    setChats((prev: any[]) => [c, ...prev])

    // 2) 새 채팅으로 이동
    router.push(`/chat/${c.id}`)
  }

  const onDeleteChat = (id: string) => {
    setChats((prev: any[]) => prev.filter((c: any) => c.id !== id))

    // 현재 보고 있는 채팅을 삭제했다면 홈으로 이동
    if (pathname === `/chat/${id}`) {
      router.push("/")
    }
  }

  return (
    <div className="h-screen w-screen flex">
      <Sidebar
        chats={chats}
        onNewChat={onNewChat}
        onDeleteChat={onDeleteChat}
        isOpen={sidebarOpen}
        onClose={onClose}
      />

      {/* Main */}
      <main className="flex-1 md:ml-64 h-full">
        {children}
      </main>
    </div>
  )
}
