"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Command, CommandInput, CommandList, CommandItem, CommandGroup } from "@/components/ui/command"
import {
  Paperclip,
  Send,
  StopCircle,
  Smile,
  Trash2,
  Wand2,
  Languages,
  BookOpen,
} from "lucide-react"

const COMMANDS = [
  { id: "summarize", label: "Summarize", icon: <Wand2 className="h-3.5 w-3.5" /> },
  { id: "translate", label: "Translate", icon: <Languages className="h-3.5 w-3.5" /> },
  { id: "explain", label: "Explain", icon: <BookOpen className="h-3.5 w-3.5" /> },
]

const EMOJIS = ["😀", "🚀", "🔥", "✨", "❤️", "👍", "🤔", "🎉"]

export default function AiChatInput({
  onSendMessage,
  onUploadFile,
  isLoading = false,
}: {
  onSendMessage: (message: string) => void
  onUploadFile?: (file: File) => void
  isLoading?: boolean
}) {
  const [input, setInput] = useState("")
  const [selectedCommands, setSelectedCommands] = useState<string[]>([])
  const [emojiOpen, setEmojiOpen] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)

  const handleSubmit = () => {
    if (!input.trim() && selectedCommands.length === 0) return
    const finalMessage =
      (selectedCommands.map((cmd) => `/${cmd}`).join(" ") + " " + input).trim()
    onSendMessage(finalMessage)
    setInput("")
    setSelectedCommands([])
    setCommandOpen(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
    if (e.key === "/" && !commandOpen) {
      e.preventDefault()
      setCommandOpen(true)
    }
  }

  const addCommand = (cmd: string) => {
    if (!selectedCommands.includes(cmd)) {
      setSelectedCommands((prev) => [...prev, cmd])
    }
    setCommandOpen(false)
  }

  const removeCommand = (cmd: string) => {
    setSelectedCommands((prev) => prev.filter((c) => c !== cmd))
  }

  const addEmoji = (emoji: string) => {
    setInput((prev) => prev + emoji)
    setEmojiOpen(false)
  }

  return (
    <div className="w-full bg-background border-t">
      <div className="flex items-end gap-2 p-3 max-w-4xl mx-auto">
        {/* File Upload */}
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 shrink-0"
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <Paperclip className="h-5 w-5" />
        </Button>
        <input
          id="file-input"
          type="file"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0] && onUploadFile) {
              onUploadFile(e.target.files[0])
            }
          }}
        />

        {/* Input & Commands Container */}
        <div className="flex flex-col flex-1 gap-2 min-w-0">
          {/* Selected Commands as tags */}
          {selectedCommands.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {selectedCommands.map((cmd) => {
                const c = COMMANDS.find((c) => c.id === cmd)
                return (
                  <Badge
                    key={cmd}
                    variant="secondary"
                    className="flex items-center gap-1 cursor-pointer hover:bg-destructive hover:text-destructive-foreground transition-colors"
                    onClick={() => removeCommand(cmd)}
                  >
                    {c?.icon} {c?.label}
                  </Badge>
                )
              })}
            </div>
          )}

          {/* Text Input with Slash Command Popover */}
          <Popover open={commandOpen} onOpenChange={setCommandOpen}>
            <PopoverTrigger asChild>
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message... (press '/' for commands)"
                className="resize-none min-h-[44px] max-h-[200px] rounded-xl px-3 py-2 text-sm bg-muted/50 border-none focus-visible:ring-1 focus-visible:ring-primary/20"
              />
            </PopoverTrigger>
            <PopoverContent className="p-0 w-56" align="start" side="top">
              <Command>
                <CommandInput placeholder="Search command..." />
                <CommandList>
                  <CommandGroup heading="Available Commands">
                    {COMMANDS.map((cmd) => (
                      <CommandItem
                        key={cmd.id}
                        onSelect={() => addCommand(cmd.id)}
                        className="flex items-center gap-2"
                      >
                        {cmd.icon}
                        <span>{cmd.label}</span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1 mb-0.5 shrink-0">
          <Popover open={emojiOpen} onOpenChange={setEmojiOpen}>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="h-10 w-10">
                <Smile className="h-5 w-5" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="grid grid-cols-4 gap-2 w-40 p-2" side="top">
              {EMOJIS.map((emoji) => (
                <button
                  key={emoji}
                  onClick={() => addEmoji(emoji)}
                  className="text-lg hover:bg-accent rounded p-1 transition-all"
                >
                  {emoji}
                </button>
              ))}
            </PopoverContent>
          </Popover>

          <Button 
            variant="ghost" 
            size="icon" 
            className="h-10 w-10 text-muted-foreground hover:text-destructive"
            onClick={() => setInput("")}
          >
            <Trash2 className="h-5 w-5" />
          </Button>

          <Button
            onClick={handleSubmit}
            disabled={!input.trim() && selectedCommands.length === 0 && !isLoading}
            variant={isLoading ? "ghost" : "default"}
            size="icon"
            className="h-10 w-10 rounded-full shrink-0"
          >
            {isLoading ? (
              <StopCircle className="h-5 w-5 animate-pulse text-destructive" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
