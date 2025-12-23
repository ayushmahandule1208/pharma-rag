"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { getMetrics, SystemMetrics } from "@/lib/api";
import { 
  FolderOpen, 
  FileText, 
  Database, 
  MessageSquare,
  Clock,
  Target,
  Cpu,
  Activity
} from "lucide-react";

export function MetricsView() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, []);

  async function loadMetrics() {
    try {
      const m = await getMetrics();
      setMetrics(m);
    } catch (e) {
      console.error("Failed to load metrics", e);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="text-muted-foreground text-sm">Loading metrics...</span>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <Activity className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Failed to load metrics</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto overflow-y-auto h-full">
      <div className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">System Metrics</h1>
        <p className="text-muted-foreground mt-1 text-sm sm:text-base">Monitor your RAG system performance</p>
      </div>

      {/* Main stats - 2 cols on mobile, 4 on larger */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
        <MetricCard
          icon={<FolderOpen className="w-4 h-4 sm:w-5 sm:h-5" />}
          label="Document Families"
          value={metrics.families}
          color="text-primary"
          bgColor="bg-primary/10"
        />
        <MetricCard
          icon={<FileText className="w-4 h-4 sm:w-5 sm:h-5" />}
          label="Document Versions"
          value={metrics.documents}
          color="text-accent"
          bgColor="bg-accent/10"
        />
        <MetricCard
          icon={<Database className="w-4 h-4 sm:w-5 sm:h-5" />}
          label="Indexed Chunks"
          value={metrics.search_units}
          color="text-violet-400"
          bgColor="bg-violet-400/10"
        />
        <MetricCard
          icon={<MessageSquare className="w-4 h-4 sm:w-5 sm:h-5" />}
          label="Total Queries"
          value={metrics.queries_logged}
          color="text-rose-400"
          bgColor="bg-rose-400/10"
        />
      </div>

      {/* Performance section */}
      <h2 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4 flex items-center gap-2">
        <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
        Query Performance
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 mb-6 sm:mb-8">
        <Card className="overflow-hidden">
          <div className="h-1 bg-gradient-to-r from-primary/50 to-primary" />
          <CardHeader>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="w-4 h-4" />
              <CardTitle className="text-xs sm:text-sm font-medium">Avg Response Time</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground tracking-tight">
              {metrics.avg_response_time || 0}
              <span className="text-sm sm:text-lg font-normal text-muted-foreground ml-1">ms</span>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <div className="h-1 bg-gradient-to-r from-accent/50 to-accent" />
          <CardHeader>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Target className="w-4 h-4" />
              <CardTitle className="text-xs sm:text-sm font-medium">Avg Relevance Score</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground tracking-tight">
              {((metrics.avg_score || 0) * 100).toFixed(0)}
              <span className="text-sm sm:text-lg font-normal text-muted-foreground ml-1">%</span>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden sm:col-span-2 lg:col-span-1">
          <div className="h-1 bg-gradient-to-r from-violet-400/50 to-violet-400" />
          <CardHeader>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Database className="w-4 h-4" />
              <CardTitle className="text-xs sm:text-sm font-medium">Vector Index</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground tracking-tight">
              {metrics.vectors || metrics.search_units}
              <span className="text-sm sm:text-lg font-normal text-muted-foreground ml-1">vectors</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System info */}
      <h2 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4 flex items-center gap-2">
        <Cpu className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
        System Information
      </h2>
      <Card className="overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-primary/30 via-accent/30 to-violet-400/30" />
        <CardContent className="pt-5 sm:pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            <InfoItem label="Embedding Model" value="all-MiniLM-L6-v2" />
            <InfoItem label="Vector Store" value="ChromaDB" />
            <InfoItem label="Database" value="SQLite" />
            <InfoItem label="LLM" value="GPT-4o-mini" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
      <div className="font-mono text-xs sm:text-sm text-foreground mt-1 bg-secondary/50 px-2 py-1 rounded inline-block break-all">
        {value}
      </div>
    </div>
  );
}

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  bgColor: string;
}

function MetricCard({ icon, label, value, color, bgColor }: MetricCardProps) {
  return (
    <Card className="overflow-hidden group hover:border-primary/30 transition-colors">
      <CardContent className="pt-4 sm:pt-5">
        <div className={`w-8 h-8 sm:w-10 sm:h-10 ${bgColor} rounded-lg sm:rounded-xl flex items-center justify-center mb-2 sm:mb-3 ${color} group-hover:scale-110 transition-transform`}>
          {icon}
        </div>
        <div className="text-xl sm:text-2xl lg:text-3xl font-bold text-foreground tracking-tight">{value}</div>
        <div className="text-xs sm:text-sm text-muted-foreground mt-0.5 sm:mt-1">{label}</div>
      </CardContent>
    </Card>
  );
}
