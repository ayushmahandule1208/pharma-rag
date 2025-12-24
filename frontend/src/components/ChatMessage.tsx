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
  Bot,
  Shield,
  Clock,
  Zap
} from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  queryType?: string;
  sources?: Source[];
  timing?: { retrieve_ms?: number; generate_ms?: number; total_ms: number };
  guardResult?: { passed: boolean; category: string; confidence: number };
}

const queryTypeConfig: Record<string, { 
  variant: "safety" | "dosing" | "efficacy" | "indication" | "muted";
  icon?: React.ReactNode;
  label: string;
}> = {
  safety: { variant: "safety", label: "Safety", icon: <AlertTriangle className="w-3 h-3" /> },
  dosing: { variant: "dosing", label: "Dosing" },
  efficacy: { variant: "efficacy", label: "Efficacy" },
  indication: { variant: "indication", label: "Indication" },
  mechanism: { variant: "muted", label: "Mechanism" },
  comparison: { variant: "muted", label: "Comparison" },
  semantic: { variant: "muted", label: "General" },
  conversational: { variant: "muted", label: "Chat", icon: <Bot className="w-3 h-3" /> },
  general_question: { variant: "muted", label: "General", icon: <Shield className="w-3 h-3" /> },
  gibberish: { variant: "muted", label: "Invalid" },
};

export function ChatMessage({ role, content, queryType, sources, timing, guardResult }: ChatMessageProps) {
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

  const typeConfig = queryType ? queryTypeConfig[queryType] : undefined;

  return (
    <div className="mb-5 sm:mb-6">
      <div className="flex items-start gap-2 sm:gap-3">
        <div className="w-7 h-7 sm:w-8 sm:h-8 bg-accent/20 rounded-full flex items-center justify-center flex-shrink-0 border border-accent/30 hidden sm:flex">
          <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-accent" />
        </div>
        
        <div className="flex-1 max-w-full sm:max-w-[85%]">
          {/* Query type and guard status badges */}
          {(queryType || guardResult) && (
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {typeConfig && (
                <Badge variant={typeConfig.variant} className="flex items-center gap-1">
                  {typeConfig.icon}
                  {typeConfig.label}
                </Badge>
              )}
              {guardResult && !guardResult.passed && (
                <Badge variant="muted" className="flex items-center gap-1 text-xs">
                  <Shield className="w-3 h-3" />
                  Handled
                </Badge>
              )}
              {timing && timing.total_ms > 0 && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {timing.total_ms}ms
                </span>
              )}
            </div>
          )}

          {/* Response content with markdown rendering */}
          <div className="bg-secondary/80 backdrop-blur-sm border border-border/50 rounded-2xl rounded-tl-md px-4 sm:px-5 py-3 sm:py-4">
            <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-headings:text-foreground prose-p:text-foreground prose-p:leading-relaxed prose-ul:text-foreground prose-ol:text-foreground prose-li:text-foreground prose-strong:text-foreground prose-strong:font-semibold prose-a:text-primary prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:before:content-[''] prose-code:after:content-['']">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  // Custom heading styles
                  h1: ({ children }) => (
                    <h1 className="text-lg font-bold mb-3 mt-4 first:mt-0 text-foreground">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-base font-semibold mb-2 mt-3 first:mt-0 text-foreground">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-sm font-semibold mb-2 mt-2 first:mt-0 text-foreground">{children}</h3>
                  ),
                  // Custom paragraph
                  p: ({ children }) => (
                    <p className="mb-3 last:mb-0 text-foreground leading-relaxed">{children}</p>
                  ),
                  // Custom list styles
                  ul: ({ children }) => (
                    <ul className="list-none space-y-1.5 mb-3 last:mb-0">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside space-y-1.5 mb-3 last:mb-0 pl-0">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="flex items-start gap-2 text-foreground">
                      <span className="text-primary mt-0.5">•</span>
                      <span className="flex-1">{children}</span>
                    </li>
                  ),
                  // Bold text
                  strong: ({ children }) => (
                    <strong className="font-semibold text-foreground">{children}</strong>
                  ),
                  // Code blocks
                  code: ({ children, className }) => {
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code className="bg-muted/80 px-1.5 py-0.5 rounded text-sm font-mono text-foreground">
                          {children}
                        </code>
                      );
                    }
                    return (
                      <code className="block bg-muted/80 p-3 rounded-lg text-sm font-mono overflow-x-auto">
                        {children}
                      </code>
                    );
                  },
                  // Links
                  a: ({ href, children }) => (
                    <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                  // Blockquotes for warnings/notes
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-primary/50 pl-4 py-1 my-3 bg-primary/5 rounded-r-lg italic text-muted-foreground">
                      {children}
                    </blockquote>
                  ),
                  // Horizontal rules
                  hr: () => (
                    <hr className="my-4 border-border/50" />
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
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
  // Calculate display score - prefer rerank, then final score
  const displayScore = source.rerank_score && source.rerank_score > 0 
    ? Math.min(source.rerank_score / 10, 1) // Normalize rerank score
    : source.score;

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
            <CheckCircle2 className="w-4 h-4 text-accent" title="Priority section" />
          )}
          {/* Score breakdown tooltip */}
          <div className="flex items-center gap-1" title={`BM25: ${source.bm25_score?.toFixed(1) || 'N/A'} | Vector: ${source.vector_score?.toFixed(2) || 'N/A'} | Rerank: ${source.rerank_score?.toFixed(1) || 'N/A'}`}>
            {source.rerank_score && source.rerank_score > 0 && (
              <Zap className="w-3 h-3 text-accent" title="Re-ranked" />
            )}
            <span className="text-xs font-mono bg-secondary px-1.5 py-0.5 rounded text-muted-foreground">
              {(displayScore * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
      
      {/* Score breakdown - show on hover or if expanded */}
      {(source.bm25_score || source.vector_score) && (
        <div className="flex gap-2 mt-2 text-[10px] text-muted-foreground">
          {source.bm25_score !== undefined && source.bm25_score > 0 && (
            <span className="bg-secondary/50 px-1.5 py-0.5 rounded">
              BM25: {source.bm25_score.toFixed(1)}
            </span>
          )}
          {source.vector_score !== undefined && source.vector_score > 0 && (
            <span className="bg-secondary/50 px-1.5 py-0.5 rounded">
              Vec: {(source.vector_score * 100).toFixed(0)}%
            </span>
          )}
          {source.rerank_score !== undefined && source.rerank_score > 0 && (
            <span className="bg-accent/20 text-accent px-1.5 py-0.5 rounded">
              Rerank: {source.rerank_score.toFixed(1)}
            </span>
          )}
        </div>
      )}
      
      {source.text && (
        <p className="mt-2 text-xs text-muted-foreground line-clamp-2 italic">
          "{source.text}"
        </p>
      )}
    </Card>
  );
}
