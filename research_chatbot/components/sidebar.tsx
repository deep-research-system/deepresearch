"use client"

import type React from "react"

import { useRouter, usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { PlusIcon, TrashIcon, MessageSquareIcon, XIcon } from "lucide-react"
import type { Chat } from "@/lib/chat-store"
import { cn } from "@/lib/utils"

interface SidebarProps {
  chats: Chat[]
  onNewChat: () => void
  onDeleteChat: (id: string) => void
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ chats, onNewChat, onDeleteChat, isOpen, onClose }: SidebarProps) {
  const router = useRouter()
  const pathname = usePathname()

  const handleChatClick = (id: string) => {
    router.push(`/chat/${id}`)
    onClose()
  }

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    onDeleteChat(id)
  }

  const sortedChats = [...chats].sort((a, b) => b.updatedAt - a.updatedAt)

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={onClose} />}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 h-full w-64 bg-sidebar border-r border-sidebar-border z-50 transform transition-transform duration-200 ease-in-out flex flex-col",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* Header */}
        <div className="p-4 border-b border-sidebar-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-sidebar-foreground">Chats</h2>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={onClose} aria-label="Close sidebar">
            <XIcon className="h-5 w-5" />
          </Button>
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <Button
            onClick={() => {
              onNewChat()
              onClose()
            }}
            className="w-full justify-start gap-2"
            variant="outline"
          >
            <PlusIcon className="h-4 w-4" />
            New Chat
          </Button>
        </div>

        {/* Chat History */}
        <ScrollArea className="flex-1 px-2">
          <div className="space-y-1 pb-4">
            {sortedChats.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No chats yet. Start a new conversation!
              </div>
            ) : (
              sortedChats.map((chat) => {
                const isActive = pathname === `/chat/${chat.id}`
                return (
                  <div
                    key={chat.id}
                    onClick={() => handleChatClick(chat.id)}
                    className={cn(
                      "group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "hover:bg-sidebar-accent/50 text-sidebar-foreground",
                    )}
                  >
                    <MessageSquareIcon className="h-4 w-4 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{chat.title}</p>
                      <p className="text-xs text-muted-foreground">{new Date(chat.updatedAt).toLocaleDateString()}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => handleDelete(e, chat.id)}
                      aria-label="Delete chat"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </Button>
                  </div>
                )
              })
            )}
          </div>
        </ScrollArea>
      </aside>
    </>
  )
}
