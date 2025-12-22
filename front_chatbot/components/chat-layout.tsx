"use client"

import type React from "react"
import { usePathname, useRouter } from "next/navigation"
import { Sidebar } from "./sidebar"
import { useChat } from "./chat-provider"

export function ChatLayout({ children }: { children: React.ReactNode }) {
  const { chats, setChats, isSidebarOpen, closeSidebar } = useChat()
  const router = useRouter()
  const pathname = usePathname()

  const handleNewChat = () => {
    router.push("/")
  }

  const handleDeleteChat = (id: string) => {
    setChats((prev) => prev.filter((chat) => chat.id !== id))
    if (pathname === `/chat/${id}`) {
      router.push("/")
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        chats={chats}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
      />
      <main className="flex-1 flex flex-col md:ml-64">{children}</main>
    </div>
  )
}
