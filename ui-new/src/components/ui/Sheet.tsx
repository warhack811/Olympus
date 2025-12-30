"use client"

import * as React from "react"
import { createPortal } from "react-dom"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

// Simple Context to manage state
const SheetContext = React.createContext<{
    open: boolean;
    setOpen: (open: boolean) => void;
} | null>(null)

export const Sheet = ({ children }: { children: React.ReactNode }) => {
    const [open, setOpen] = React.useState(false)
    return (
        <SheetContext.Provider value={{ open, setOpen }}>
            {children}
        </SheetContext.Provider>
    )
}

export const SheetTrigger = ({ className, children, asChild }: any) => {
    const ctx = React.useContext(SheetContext)
    if (!ctx) return null

    return (
        <div onClick={() => ctx.setOpen(true)} className={cn("cursor-pointer", className)}>
            {children}
        </div>
    )
}

export const SheetContent = ({ side = "left", className, children }: { side?: "left" | "right", className?: string, children: React.ReactNode }) => {
    const ctx = React.useContext(SheetContext)
    if (!ctx) return null

    if (!ctx.open) return null

    return createPortal(
        <div className="fixed inset-0 z-50 flex">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
                onClick={() => ctx.setOpen(false)}
            />

            {/* Drawer */}
            <div className={cn(
                "relative z-50 flex flex-col bg-background shadow-lg transition-transform duration-300 ease-in-out h-full",
                side === "left" && "animate-in slide-in-from-left",
                side === "right" && "animate-in slide-in-from-right",
                className
            )}>
                <button
                    onClick={() => ctx.setOpen(false)}
                    className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none disabled:pointer-events-none data-[state=open]:bg-secondary text-white"
                >
                    <X className="h-4 w-4" />
                    <span className="sr-only">Close</span>
                </button>
                {children}
            </div>
        </div>,
        document.body
    )
}

// Missing exports added to satisfy index.ts
export const SheetHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
    <div className={cn("flex flex-col space-y-2 text-center sm:text-left", className)} {...props} />
)
export const SheetFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
    <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", className)} {...props} />
)
export const SheetTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-lg font-semibold text-foreground", className)} {...props} />
))
export const SheetDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
))
export const SheetClose = SheetTrigger // Alias for compatibility
