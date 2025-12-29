"use client"

import { useState } from "react"
import type { Agent } from "@/lib/chat-store"

export function ChatInput({
  disabled,
  agent,
  onAgentChange,
  onSend,
}: {
  disabled?: boolean
  agent: Agent
  onAgentChange: (a: Agent) => void
  onSend: (text: string) => void
}) {
  const [text, setText] = useState("")

  function submit() {
    const t = text.trim()
    if (!t) return

    // DeepResearch만 실제 전송
    if (agent !== "DeepResearch") {
      // 선택은 유지하되, 실제 사용은 막고 DeepResearch로 복귀
      alert("현재는 DeepResearch 모드만 지원합니다.")
      onAgentChange("DeepResearch")
      return
    }

    onSend(t)
    setText("")
  }

  return (
    <div className="p-3 flex gap-2 items-end">
      <select
        className="border rounded px-2 py-1 text-sm"
        value={agent}
        onChange={(e) => onAgentChange(e.target.value as Agent)}
        disabled={disabled}
      >
        <option value="General">General</option>
        <option value="DeepResearch">DeepResearch</option>
        <option value="MeetingSummary">MeetingSummary</option>
      </select>

      <textarea
        className="flex-1 border rounded p-2 text-sm resize-none"
        rows={2}
        placeholder="Type a message... (Shift+Enter for new line)"
        value={text}
        disabled={disabled}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
      />

      <button className="border rounded px-3 py-2 text-sm" onClick={submit} disabled={disabled}>
        Send
      </button>
    </div>
  )
}
