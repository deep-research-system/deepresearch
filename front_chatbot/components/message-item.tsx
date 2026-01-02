"use client"

import { cn } from "@/lib/utils"
import type { Message } from "@/lib/chat-store"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import React from "react"

export function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    // row는 항상 전체폭
    <div className="w-full py-3">
      {/* 공통: 오른쪽 기준선으로 정렬 (GPT처럼 우측 라인 맞추기) */}
      <div className="flex w-full justify-end">
        <div
          className={cn(
            // 공통 텍스트 스타일
            "rounded-2xl px-4 py-2.5 leading-relaxed",
            // 핵심: 폭 차등
            isUser ? "max-w-[55%]" : "max-w-[80%] w-full",
            // 스타일
            isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
          )}
        >
          {!isUser && (message as any).statusText ? (
            <p className="text-xs opacity-80 mb-2 whitespace-pre-wrap break-words">
              {(message as any).statusText}
            </p>
          ) : null}

          <div className="prose prose-neutral dark:prose-invert prose-lg max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}
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
