"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { PlusIcon, CheckIcon } from "lucide-react"
import type { Agent } from "@/lib/chat-store"
import { cn } from "@/lib/utils"

// 에이전트 +버튼

interface AgentSelectorProps {
  selectedAgent: Agent
  onAgentChange: (agent: Agent) => void
}


// 에이전트 옵션들
const agents: { value: Agent; label: string; description: string }[] = [
  { value: "General", label: "General", description: "General purpose assistant" },
  { value: "DeepResearch", label: "Deep Research", description: "In-depth research and analysis" },
  { value: "MeetingSummary", label: "Meeting Summary", description: "Summarize meetings and notes" },
]

// 에이전트 선택 컴포넌트
export function AgentSelector({ selectedAgent, onAgentChange }: AgentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

// 클릭 외부 감지 훅
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [isOpen])

//  선택된 에이전트 데이터
  const selectedAgentData = agents.find((a) => a.value === selectedAgent)

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="gap-1.5"
        aria-label="Select agent"
      >
        <PlusIcon className="h-3.5 w-3.5" />
        <span className="text-xs">{selectedAgentData?.label}</span>
      </Button>

      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-64 bg-popover border border-border rounded-lg shadow-lg z-50">
          <div className="p-2">
            <p className="text-xs font-semibold text-muted-foreground px-2 py-1.5">Select Agent</p>
            <div className="space-y-1">
              {agents.map((agent) => (
                <button
                  key={agent.value}
                  onClick={() => {
                    onAgentChange(agent.value)
                    setIsOpen(false)
                  }}
                  className={cn(
                    "w-full text-left px-2 py-2 rounded-md hover:bg-accent transition-colors flex items-start gap-2",
                    selectedAgent === agent.value && "bg-accent",
                  )}
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium">{agent.label}</p>
                    <p className="text-xs text-muted-foreground">{agent.description}</p>
                  </div>
                  {selectedAgent === agent.value && <CheckIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
