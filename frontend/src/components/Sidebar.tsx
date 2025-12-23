"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Pill, 
  ChevronDown, 
  ChevronRight, 
  FileText,
  CheckCircle2,
  BarChart3,
  FolderOpen,
  Beaker,
  X
} from "lucide-react";
import { DocumentFamily, getDocuments, getVersions, DocumentVersion } from "@/lib/api";

interface SidebarProps {
  onViewChange: (view: "chat" | "metrics") => void;
  currentView: "chat" | "metrics";
  onClose?: () => void;
}

export function Sidebar({ onViewChange, currentView, onClose }: SidebarProps) {
  const [documents, setDocuments] = useState<DocumentFamily[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [versions, setVersions] = useState<Record<string, DocumentVersion[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (e) {
      console.error("Failed to load documents", e);
    } finally {
      setLoading(false);
    }
  }

  async function toggleExpand(familyId: string) {
    if (expanded === familyId) {
      setExpanded(null);
      return;
    }

    setExpanded(familyId);

    // Load versions if not cached
    if (!versions[familyId]) {
      try {
        const v = await getVersions(familyId);
        setVersions((prev) => ({ ...prev, [familyId]: v }));
      } catch (e) {
        console.error("Failed to load versions", e);
      }
    }
  }

  return (
    <aside className="w-72 sm:w-80 lg:w-72 bg-card/95 backdrop-blur-md border-r border-border flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary/20 to-primary/5 rounded-xl flex items-center justify-center border border-primary/20">
              <Beaker className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="font-semibold text-foreground text-lg tracking-tight">PharmaRAG</h1>
              <p className="text-xs text-muted-foreground">Regulatory Intelligence</p>
            </div>
          </div>
          {/* Mobile close button */}
          {onClose && (
            <button
              onClick={onClose}
              className="lg:hidden p-2 hover:bg-secondary rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="p-3 border-b border-border">
        <Button
          variant={currentView === "chat" ? "default" : "ghost"}
          className="w-full justify-start gap-3 mb-1.5"
          onClick={() => onViewChange("chat")}
        >
          <FolderOpen className="w-4 h-4" />
          Query
        </Button>
        <Button
          variant={currentView === "compare" ? "default" : "ghost"}
          className="w-full justify-start gap-3 mb-1.5"
          onClick={() => onViewChange("compare")}
        >
          <ArrowLeftRight className="w-4 h-4" />
          Compare
        </Button>
        <Button
          variant={currentView === "metrics" ? "default" : "ghost"}
          className="w-full justify-start gap-3"
          onClick={() => onViewChange("metrics")}
        >
          <BarChart3 className="w-4 h-4" />
          Metrics
        </Button>
      </div>

      {/* Documents list */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3 px-2">
          Documents
        </div>

        {loading ? (
          <div className="px-2 py-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Loading...
            </div>
          </div>
        ) : documents.length === 0 ? (
          <div className="px-3 py-6 text-sm text-muted-foreground text-center">
            <Pill className="w-8 h-8 mx-auto mb-2 opacity-30" />
            No documents ingested yet
          </div>
        ) : (
          <div className="space-y-1">
            {documents.map((doc) => (
              <div key={doc.family_id}>
                <button
                  onClick={() => toggleExpand(doc.family_id)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-secondary/80 transition-all text-left group active:scale-[0.98]"
                >
                  {expanded === doc.family_id ? (
                    <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  )}
                  <Pill className="w-4 h-4 text-primary flex-shrink-0" />
                  <span className="flex-1 text-sm font-medium truncate group-hover:text-foreground transition-colors">
                    {doc.drug_name}
                  </span>
                  <Badge variant="muted" className="text-xs flex-shrink-0">
                    {doc.version_count}
                  </Badge>
                </button>

                {/* Versions */}
                {expanded === doc.family_id && versions[doc.family_id] && (
                  <div className="ml-6 mt-1 space-y-0.5 border-l border-border pl-3">
                    {versions[doc.family_id].map((v) => (
                      <div
                        key={v.doc_id}
                        className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-secondary/50 text-sm transition-colors"
                      >
                        <FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                        <span className="text-muted-foreground">
                          v{v.version_num}
                        </span>
                        {v.version_date && (
                          <span className="text-xs text-muted-foreground/70 truncate">
                            {v.version_date}
                          </span>
                        )}
                        {v.is_latest === 1 && (
                          <CheckCircle2 className="w-3.5 h-3.5 text-accent ml-auto flex-shrink-0" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer stats */}
      <div className="p-4 border-t border-border bg-secondary/30">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{documents.length} families</span>
          <span className="text-primary font-medium">{documents.reduce((acc, d) => acc + d.version_count, 0)} versions</span>
        </div>
      </div>
    </aside>
  );
}
