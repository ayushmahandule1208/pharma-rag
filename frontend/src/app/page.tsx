"use client";

import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatView } from "@/components/ChatView";
import { MetricsView } from "@/components/MetricsView";
import { CompareView } from "@/components/CompareView";
import { Menu, X } from "lucide-react";

export default function Home() {
  const [view, setView] = useState<"chat" | "metrics" | "compare">("chat");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleViewChange = (newView: "chat" | "metrics" | "compare") => {
    setView(newView);
    setSidebarOpen(false); // Close sidebar on mobile when view changes
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - hidden on mobile, slide-out drawer when open */}
      <div className={`
        fixed lg:relative inset-y-0 left-0 z-50
        transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <Sidebar 
          onViewChange={handleViewChange} 
          currentView={view} 
          onClose={() => setSidebarOpen(false)}
        />
      </div>
      
      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center justify-between p-4 border-b border-border bg-card/80 backdrop-blur-sm">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-secondary rounded-xl transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="font-semibold text-foreground">PharmaRAG</h1>
          <div className="w-9" /> {/* Spacer for centering */}
        </div>

        {/* View content */}
        <div className="flex-1 overflow-hidden">
          {view === "chat" && <ChatView />}
          {view === "compare" && <CompareView />}
          {view === "metrics" && <MetricsView />}
        </div>
      </main>
    </div>
  );
}
