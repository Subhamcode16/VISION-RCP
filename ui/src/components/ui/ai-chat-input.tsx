"use client"

import { useState, useRef, useEffect } from "react"
import { Plus, Mic, Trash2, Wand2, Languages, BookOpen, Smile } from "lucide-react"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandInput, CommandList, CommandItem, CommandGroup } from "@/components/ui/command"
import "./ai-chat-input.css"

const COMMANDS = [
  { id: "summarize", label: "Summarize", icon: <Wand2 className="h-3.5 w-3.5" /> },
  { id: "translate", label: "Translate", icon: <Languages className="h-3.5 w-3.5" /> },
  { id: "explain", label: "Explain", icon: <BookOpen className="h-3.5 w-3.5" /> },
]

const EMOJIS = ["😀", "🚀", "🔥", "✨", "❤️", "👍", "🤔", "🎉"]

interface AiChatInputProps {
  onSendMessage: (message: string) => void
  onUploadFile?: (file: File) => void
  isLoading?: boolean
  agentStatus?: string
}

export default function AiChatInput({
  onSendMessage,
  onUploadFile,
  isLoading = false,
  agentStatus = "idle"
}: AiChatInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const isOnline = agentStatus === "running" || agentStatus === "awaiting_approval"

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${textarea.scrollHeight}px`
    }
  }, [input])

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return
    onSendMessage(input.trim())
    setInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const addCommand = (cmd: string) => {
    setInput((prev) => `/${cmd} ` + prev)
  }

  const addEmoji = (emoji: string) => {
    setInput((prev) => prev + emoji)
  }

  return (
    <div className="ai-chat-pill">
      {/* Hidden Features Dropdown (+) */}
      <Popover>
        <PopoverTrigger asChild>
          <button className="ai-chat-pill__btn" title="More Features">
            <Plus size={20} strokeWidth={2.5} />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-56 p-2 bg-zinc-900/90 backdrop-blur-xl border-zinc-800" side="top" align="start">
          <div className="flex flex-col gap-1">
            <div className="text-[10px] font-bold text-zinc-500 px-2 py-1 tracking-widest uppercase">Quick Actions</div>
            <Command className="bg-transparent">
              <CommandList>
                <CommandGroup>
                  {COMMANDS.map((cmd) => (
                    <CommandItem 
                      key={cmd.id} 
                      onSelect={() => addCommand(cmd.id)}
                      className="flex items-center gap-2 text-zinc-300 hover:text-white"
                    >
                      {cmd.icon}
                      <span className="text-xs">{cmd.label}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
            <div className="h-[1px] bg-zinc-800 my-1" />
            <div className="flex flex-wrap gap-1 p-1">
              {EMOJIS.map((emoji) => (
                <button 
                  key={emoji} 
                  onClick={() => addEmoji(emoji)}
                  className="hover:bg-zinc-800 p-1 rounded transition-colors text-sm"
                >
                  {emoji}
                </button>
              ))}
            </div>
            <div className="h-[1px] bg-zinc-800 my-1" />
            <button 
              className="flex items-center gap-2 text-xs text-zinc-400 hover:text-red-400 px-2 py-1.5 transition-colors"
              onClick={() => setInput("")}
            >
              <Trash2 size={14} />
              <span>Clear Input</span>
            </button>
          </div>
        </PopoverContent>
      </Popover>

      {/* Input Field */}
      <div className="ai-chat-pill__input-container">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything..."
          className="ai-chat-pill__textarea"
          rows={1}
        />
      </div>

      {/* Status Dot */}
      <div className={`ai-chat-pill__status ${isOnline ? 'ai-chat-pill__status--online' : ''}`} />

      {/* Mic Icon (Aesthetic) */}
      <button className="ai-chat-pill__btn opacity-60 hover:opacity-100 transition-opacity">
        <Mic size={18} />
      </button>

      {/* Branded Send Button (V-Sign) */}
      <button 
        className="ai-chat-pill__send"
        onClick={handleSubmit}
        disabled={!input.trim() || isLoading}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="ai-chat-pill__v-sign"
        >
          <path
            d="M20 30L50 80L80 30"
            stroke="currentColor"
            strokeWidth="14"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  )
}
