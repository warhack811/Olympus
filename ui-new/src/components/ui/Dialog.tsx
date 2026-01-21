"use client"

import * as React from "react"
import { createPortal } from "react-dom"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

const DialogContext = React.createContext<{
    open: boolean;
    setOpen: (open: boolean) => void;
} | null>(null)

export const Dialog = ({ children, open, onOpenChange }: {
    children: React.ReactNode,
    open?: boolean,
    onOpenChange?: (open: boolean) => void
}) => {
    const [internalOpen, setInternalOpen] = React.useState(false)
    const isControlled = open !== undefined
    const isOpen = isControlled ? open : internalOpen

    const handleOpenChange = (newOpen: boolean) => {
        if (!isControlled) setInternalOpen(newOpen)
        onOpenChange?.(newOpen)
    }

    return (
        <DialogContext.Provider value={{ open: isOpen, setOpen: handleOpenChange }}>
            {children}
        </DialogContext.Provider>
    )
}

export const DialogTrigger = ({ children, asChild }: any) => {
    const ctx = React.useContext(DialogContext)
    if (!ctx) return null
    return (
        <div onClick={() => ctx.setOpen(true)} className="cursor-pointer inline-block">
            {children}
        </div>
    )
}

export const DialogContent = ({ children, className }: { children: React.ReactNode, className?: string }) => {
    const ctx = React.useContext(DialogContext)
    if (!ctx || !ctx.open) return null

    return createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="fixed inset-0 bg-black/80 backdrop-blur-sm"
                onClick={() => ctx.setOpen(false)}
            />
            <div className={cn(
                "relative z-50 grid w-full max-w-lg gap-4 border bg-background p-6 shadow-lg duration-200 sm:rounded-lg animate-in fade-in-0 zoom-in-95",
                className
            )}>
                <button
                    onClick={() => ctx.setOpen(false)}
                    className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
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

export const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
    <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)} {...props} />
)

export const DialogTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className, ...props }, ref) => (
    <h2 ref={ref} className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />
))

export const DialogDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
))
