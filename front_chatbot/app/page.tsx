"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useChat } from "@/components/chat-provider"
import { createChat } from "@/lib/chat-store"

export default function HomePage() {
  const router = useRouter()
  const { setChats } = useChat()
  const ranRef = useRef(false)

  useEffect(() => {
    // StrictMode(dev) 2회 실행 방지
    if (ranRef.current) return
    ranRef.current = true

    const c = createChat("DeepResearch")

    // 사내용 정책: 항상 깨끗하게 1개만 시작
    setChats([c])

    // 바로 채팅 화면으로 진입
    router.replace(`/chat/${c.id}`)
  }, [router, setChats])

  return null
}
