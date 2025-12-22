"use client"

import { Button } from "@/components/ui/button"
import { MenuIcon } from "lucide-react"

// 채팅 해더 컴포넌트(모바일)

interface ChatHeaderProps {
  title: string
  onMenuClick: () => void
}


export function ChatHeader({ title, onMenuClick }: ChatHeaderProps) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-3 px-4 py-3 bg-background border-b border-border">
      <Button variant="ghost" size="icon" onClick={onMenuClick} aria-label="Toggle sidebar" className="md:hidden">
        <MenuIcon className="h-5 w-5" />
      </Button>
      <h1 className="text-lg font-semibold truncate">{title}</h1>
    </header>
  )
}
