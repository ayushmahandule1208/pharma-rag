"use client";

import { cn } from "@/lib/utils";
import { forwardRef } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full bg-secondary/80 border border-border rounded-xl px-4 py-3",
          "text-foreground placeholder:text-muted-foreground",
          "focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50",
          "transition-all duration-200",
          "hover:border-border/80",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
