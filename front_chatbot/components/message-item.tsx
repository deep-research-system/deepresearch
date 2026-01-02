"use client"

import { cn } from "@/lib/utils"
import type { Message } from "@/lib/chat-store"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex w-full py-4 px-4", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
        )}
      >
        {!isUser && message.statusText ? (
          <p className="text-xs opacity-80 mb-2 whitespace-pre-wrap break-words">
            {message.statusText}
          </p>
        ) : null}

        <div className="break-words">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ node, ...props }) => (
                <a {...props} target="_blank" rel="noreferrer noopener" className="underline" />
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        
        <time className="text-xs opacity-70 mt-1 block">
          {new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </time>
      </div>
    </div>
  )
}
