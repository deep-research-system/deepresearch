"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { SendIcon } from "lucide-react"
import { AgentSelector } from "./agent-selector"
import type { Agent } from "@/lib/chat-store"



// 입력창 컴포넌트

// onsend: 메시지 전송 콜백
// disabled: 입력 비활성화 여부
// agent: 선택된 에이전트
// onAgentChange: 에이전트 변경 콜백  
interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  agent: Agent
  onAgentChange: (agent: Agent) => void
}

export function ChatInput({ onSend, disabled, agent, onAgentChange }: ChatInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput("")
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto"
      }
    }
  }


  // shift+enter 줄바꿈, enter 전송
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }
// 입력창 높이 자동 조절
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [input])

  return (
    <div className="border-t border-border bg-background p-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <div className="flex items-end gap-2">
          <AgentSelector selectedAgent={agent} onAgentChange={onAgentChange} />
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message... (Shift+Enter for new line)"
              disabled={disabled}
              className="min-h-[44px] max-h-[200px] resize-none pr-12"
              rows={1}
            />
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || disabled}
              className="absolute right-1 bottom-1 h-8 w-8"
              aria-label="Send message"
            >
              <SendIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </form>
    </div>
  )
}
