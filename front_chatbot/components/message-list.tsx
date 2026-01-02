"use client"

import { useEffect, useRef } from "react"
import type { Message } from "@/lib/chat-store"
import { MessageItem } from "@/components/message-item"

export function MessageList({ messages }: { messages: Message[] }) {
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])

  if (!messages || messages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <div className="text-lg font-medium">Start a conversation</div>
          <div className="text-sm">Send a message to begin</div>
        </div>
      </div>
    )
  }

  return (
    // 스크롤은 전체폭, 내부에 중앙 컬럼
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl px-4">
        {messages.map((m) => (
          <MessageItem key={m.id} message={m} />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
