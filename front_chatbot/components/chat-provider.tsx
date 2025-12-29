"use client"

import React, { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { Chat } from "@/lib/chat-store"
import { saveChats } from "@/lib/chat-store"

type ChatCtx = {
  chats: Chat[]
  setChats: React.Dispatch<React.SetStateAction<Chat[]>>
  sidebarOpen: boolean
  toggleSidebar: () => void
  clearAllChats: () => void
}

const STORAGE_KEY = "chatbot-history"
const Ctx = createContext<ChatCtx | null>(null)

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [chats, setChats] = useState<Chat[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // ✅ 앱 시작 시: 기록은 지우되, state를 "덮어쓰지 않는다"
  // (app/page.tsx가 setChats([newChat]) 하는 걸 유지하기 위해서)
  useEffect(() => {
    if (typeof window === "undefined") return
    localStorage.removeItem(STORAGE_KEY)
    // ❌ setChats([]) 금지: 여기서 비우면 /에서 만든 chat이 바로 사라짐
  }, [])

  // 저장(선택): chats가 있을 때만 저장
  useEffect(() => {
    if (chats.length) saveChats(chats)
  }, [chats])

  const clearAllChats = () => {
    if (typeof window !== "undefined") localStorage.removeItem(STORAGE_KEY)
    setChats([])
  }

  const value = useMemo(
    () => ({
      chats,
      setChats,
      sidebarOpen,
      toggleSidebar: () => setSidebarOpen((v) => !v),
      clearAllChats,
    }),
    [chats, sidebarOpen],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useChat() {
  const v = useContext(Ctx)
  if (!v) throw new Error("useChat must be used within ChatProvider")
  return v
}
