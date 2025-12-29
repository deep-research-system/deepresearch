"use client"

export type Agent = "General" | "DeepResearch" | "MeetingSummary"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt: number
  turnId?: string
  statusText?: string
}

export interface Chat {
  id: string
  title: string
  updatedAt: number
  agent: Agent
  messages: Message[]
}

const STORAGE_KEY = "chatbot-history"

export function loadChats(): Chat[] {
  if (typeof window === "undefined") return []
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

export function saveChats(chats: Chat[]): void {
  if (typeof window === "undefined") return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats))
  } catch (error) {
    console.error("Failed to save chats:", error)
  }
}

export function createChat(agent: Agent = "DeepResearch"): Chat {
  return {
    id: `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    title: "New Chat",
    updatedAt: Date.now(),
    agent,
    messages: [],
  }
}
