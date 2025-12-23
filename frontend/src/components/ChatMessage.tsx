"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Source } from "@/lib/api";
import { 
  AlertTriangle, 
  FileText, 
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  User,
  Bot
} from "lucide-react";
import { useState } from "react";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  queryType?: string;
  sources?: Source[];
}

const queryTypeVariants: Record<string, "safety" | "dosing" | "efficacy" | "indication" | "muted"> = {
  safety: "safety",
  dosing: "dosing",
  efficacy: "efficacy",
  indication: "indication",
  mechanism: "muted",
  comparison: "muted",
};

export function ChatMessage({ role, content, queryType, sources }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);

  if (role === "user") {
    return (
      <div className="flex justify-end mb-4 sm:mb-5">
        <div className="flex items-start gap-2 sm:gap-3 max-w-[90%] sm:max-w-[80%]">
          <div className="bg-gradient-to-br from-primary to-primary/80 text-primary-foreground rounded-2xl rounded-br-md px-4 sm:px-5 py-2.5 sm:py-3 shadow-glow-sm text-sm sm:text-base">
            {content}
          </div>
          <div className="w-7 h-7 sm:w-8 sm:h-8 bg-primary/20 rounded-full flex items-center justify-center flex-shrink-0 border border-primary/30 hidden sm:flex">
            <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-primary" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-5 sm:mb-6">
      <div className="flex items-start gap-2 sm:gap-3">
        <div className="w-7 h-7 sm:w-8 sm:h-8 bg-accent/20 rounded-full flex items-center justify-center flex-shrink-0 border border-accent/30 hidden sm:flex">
          <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-accent" />
        </div>
        
        <div className="flex-1 max-w-full sm:max-w-[85%]">
          {/* Query type badge */}
          {queryType && (
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={queryTypeVariants[queryType] || "muted"}>
                {queryType}
              </Badge>
            </div>
          )}

          {/* Response content */}
          <div className="bg-secondary/80 backdrop-blur-sm border border-border/50 rounded-2xl rounded-tl-md px-4 sm:px-5 py-3 sm:py-4">
            <div className="markdown-content text-foreground whitespace-pre-wrap leading-relaxed text-sm sm:text-base">
              {content}
            </div>

            {/* Sources section */}
            {sources && sources.length > 0 && (
              <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-border/50">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
                >
                  <FileText className="w-4 h-4 group-hover:text-primary transition-colors" />
                  <span>{sources.length} Sources</span>
                  {showSources ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {showSources && (
                  <div className="mt-2 sm:mt-3 space-y-2">
                    {sources.map((source, idx) => (
                      <SourceCard key={idx} source={source} index={idx + 1} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Disclaimer */}
          {queryType === "safety" && (
            <div className="flex items-center gap-2 mt-2 sm:mt-2.5 text-xs text-warning px-1">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Consult full prescribing information for complete safety data</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  return (
    <Card className="bg-muted/50 border-border/30 p-2.5 sm:p-3 hover:border-primary/30 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
          <span className="flex items-center justify-center w-5 h-5 bg-primary/20 text-primary text-xs font-semibold rounded flex-shrink-0">
            {index}
          </span>
          <div className="min-w-0">
            <div className="font-medium text-sm text-foreground truncate">
              {source.drug}
            </div>
            <div className="text-xs text-muted-foreground truncate">
              {source.section}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
          {source.is_priority && (
            <CheckCircle2 className="w-4 h-4 text-accent" />
          )}
          <span className="text-xs font-mono bg-secondary px-1.5 py-0.5 rounded text-muted-foreground">
            {(source.score * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      {source.text && (
        <p className="mt-2 text-xs text-muted-foreground line-clamp-2 italic">
          "{source.text}"
        </p>
      )}
    </Card>
  );
}
