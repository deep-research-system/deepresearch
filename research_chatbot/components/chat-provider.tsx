"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { loadChats, saveChats, type Chat } from "@/lib/chat-store"

type ChatContextValue = {
  chats: Chat[]
  setChats: React.Dispatch<React.SetStateAction<Chat[]>>
  isSidebarOpen: boolean
  openSidebar: () => void
  closeSidebar: () => void
  toggleSidebar: () => void
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [chats, setChats] = useState<Chat[]>([])
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  useEffect(() => {
    setChats(loadChats())
  }, [])

  useEffect(() => {
    saveChats(chats)
  }, [chats])

  const value = useMemo(
    () => ({
      chats,
      setChats,
      isSidebarOpen,
      openSidebar: () => setIsSidebarOpen(true),
      closeSidebar: () => setIsSidebarOpen(false),
      toggleSidebar: () => setIsSidebarOpen((v) => !v),
    }),
    [chats, isSidebarOpen],
  )

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error("useChat must be used within ChatProvider")
  return ctx
}
