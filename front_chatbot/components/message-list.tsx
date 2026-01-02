"use client"

import { useEffect, useRef } from "react"
import type { Message } from "@/lib/chat-store"
import { MessageItem } from "@/components/message-item"

export function MessageList({ messages }: { messages: Message[] }) {
  // 자동스크롤용용
  const endRef = useRef<HTMLDivElement | null>(null)
  //  메시지 추가시 자동스크롤
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])
  // 메시지가 하나도없을때 빈 ui
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
    <div className="h-full overflow-y-auto">
      {messages.map((m) => (
        <MessageItem key={m.id} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  )
}
