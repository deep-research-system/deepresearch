// front_chatbot/app/layout.tsx
import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import "./globals.css"

import { ChatProvider } from "@/components/chat-provider"
import { ChatLayout } from "@/components/chat-layout"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Deepresearch",
  description: "A modern chatbot interface with multiple AI agents",
  generator: "v0.app",
  icons: {
    icon: [
      { url: "/icon-light-32x32.png", media: "(prefers-color-scheme: light)" },
      { url: "/icon-dark-32x32.png", media: "(prefers-color-scheme: dark)" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    apple: "/apple-icon.png",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="font-sans antialiased" suppressHydrationWarning>
        <ChatProvider>
          <ChatLayout>{children}</ChatLayout>
        </ChatProvider>

        {/* 개발 중에는 hydration 이슈/확장프로그램 주입과 섞여 경고가 커질 수 있어 production만 */}
        {process.env.NODE_ENV === "production" ? <Analytics /> : null}
      </body>
    </html>
  )
}
