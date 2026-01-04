"use client"

import { cn } from "@/lib/utils"
import type { Message } from "@/lib/chat-store"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import React from "react"

export function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    <div className="w-full py-3">
      {/* user=우측, assistant=좌측 */}
      <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 leading-relaxed",
            // 폭: user는 조금 좁게, assistant는 넓게(하지만 w-full은 제거)
            isUser ? "max-w-[55%]" : "max-w-[80%]",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
          )}
        >
          {!isUser && (message as any).statusText ? (
            <p className="text-xs opacity-80 mb-2 whitespace-pre-wrap break-words">
              {(message as any).statusText}
            </p>
          ) : null}

          <div className="prose prose-neutral dark:prose-invert prose-lg max-w-none">
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
            {new Date(message.createdAt).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </time>
        </div>
      </div>
    </div>
  )
}
