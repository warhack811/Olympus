/**
 * MessageList Component
 * 
 * Renders list of messages with animations and reply support.
 * Basitleştirilmiş versiyon - mesajlar olduğu gibi gösterilir.
 */

import { motion } from 'framer-motion'
import type { Message } from '@/types'
import { MessageBubble } from './MessageBubble'

interface MessageListProps {
    messages: Message[]
    onReply?: (message: Message) => void
    onOpenLightbox?: (url: string) => void
}

export function MessageList({ messages, onReply, onOpenLightbox }: MessageListProps) {
    return (
        <div className="px-2 md:px-8 py-6 space-y-6">
            {messages.map((message, index) => (
                <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                        duration: 0.3,
                        delay: index === messages.length - 1 ? 0 : 0,
                        ease: [0.16, 1, 0.3, 1]
                    }}
                >
                    <MessageBubble
                        message={message}
                        onReply={onReply}
                        onOpenLightbox={onOpenLightbox}
                    />
                </motion.div>
            ))}
        </div>
    )
}
