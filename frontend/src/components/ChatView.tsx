"use client";

import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ChatMessage } from "@/components/ChatMessage";
import { queryRAG, QueryResponse, Source } from "@/lib/api";
import { Send, Loader2, Sparkles, Beaker } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  queryType?: string;
  sources?: Source[];
}

const EXAMPLE_QUERIES = [
  "What are the side effects of Ozempic?",
  "What is Ozempic approved for?",
  "What is the dosage for Ozempic?",
  "How does Ozempic work?",
];

export function ChatView() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await queryRAG(userMessage.content);
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        queryType: response.query_type,
        sources: response.sources,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, there was an error processing your query. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  function handleExampleClick(query: string) {
    setInput(query);
  }

  return (
    <div className="flex flex-col h-full bg-background/50">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent rounded-2xl sm:rounded-3xl flex items-center justify-center mb-4 sm:mb-6 border border-primary/20 glow-primary">
              <Beaker className="w-8 h-8 sm:w-10 sm:h-10 text-primary" />
            </div>
            <h2 className="text-xl sm:text-2xl font-semibold mb-2 sm:mb-3 tracking-tight">Ask about FDA drug labels</h2>
            <p className="text-muted-foreground mb-6 sm:mb-8 max-w-md leading-relaxed text-sm sm:text-base">
              Get AI-powered answers from regulatory documents with source citations
            </p>
            
            {/* Example queries - stacked on mobile, wrapped on larger screens */}
            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:gap-2.5 justify-center w-full sm:max-w-xl">
              {EXAMPLE_QUERIES.map((query) => (
                <button
                  key={query}
                  onClick={() => handleExampleClick(query)}
                  className="px-4 py-2.5 bg-secondary/70 hover:bg-secondary border border-border/50 hover:border-primary/30 rounded-xl text-sm transition-all duration-200 hover:shadow-glow-sm text-left sm:text-center active:scale-[0.98]"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                queryType={message.queryType}
                sources={message.sources}
              />
            ))}
            
            {loading && (
              <div className="flex items-center gap-3 text-muted-foreground mb-4 px-3 sm:px-4 py-3 bg-secondary/50 rounded-xl w-fit">
                <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                <span className="text-sm">Searching documents...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-border bg-card/50 backdrop-blur-sm p-3 sm:p-4 lg:p-5">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-2 sm:gap-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about drug labels..."
            disabled={loading}
            className="flex-1 text-sm sm:text-base"
          />
          <Button type="submit" disabled={loading || !input.trim()} size="icon" className="px-3 sm:px-4 flex-shrink-0">
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
