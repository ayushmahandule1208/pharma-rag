"use client";

import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "safety" | "dosing" | "efficacy" | "indication" | "muted";
  className?: string;
}

const variants = {
  default: "bg-primary/15 text-primary border-primary/25",
  safety: "bg-destructive/15 text-destructive border-destructive/25",
  dosing: "bg-cyan-500/15 text-cyan-400 border-cyan-500/25",
  efficacy: "bg-accent/15 text-accent border-accent/25",
  indication: "bg-violet-500/15 text-violet-400 border-violet-500/25",
  muted: "bg-muted text-muted-foreground border-border",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full border",
        "transition-colors duration-200",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
