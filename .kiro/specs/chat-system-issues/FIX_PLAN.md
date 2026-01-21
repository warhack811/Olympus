# Chat System Issues - Production-Ready Fix Plan

**Date**: January 21, 2026  
**Status**: READY FOR IMPLEMENTATION  
**Severity**: CRITICAL (All 3 issues block production)

---

## Fix Overview

| Issue | Root Cause | Fix Strategy | Complexity | Time |
|-------|-----------|--------------|-----------|------|
| Welcome Screen | `isLoadingHistory` global state | Separate initial load flag | Medium | 30 min |
| AI Message Deleted | Messages not persisted on refresh | Hydrate messages on app startup | High | 1 hour |
| Old Conversation | Race condition in conversation selection | Add conversation ID snapshot | Medium | 45 min |

---

## FIX 1: Welcome Screen Not Showing

### Root Cause
- `isLoadingHistory` is global state
- On app startup, `useConversations()` sets `isLoadingHistory = true`
- ChatArea checks `showLoading` before `showWelcome`
- Loading spinner shown instead of welcome screen

### Solution
Create separate `isInitialLoad` flag for first-time app load, distinct from conversation-specific loading.

### Implementation

**File**: `ui-new/src/stores/chatStore.ts`

**Changes**:
1. Add new state field:
   ```typescript
   isInitialLoad: boolean  // First-time app load
   ```

2. Add action:
   ```typescript
   setInitialLoad: (isLoading: boolean) => void
   ```

3. Update persist config to NOT persist `isInitialLoad` (always false on startup)

**File**: `ui-new/src/components/chat/ChatArea.tsx`

**Changes**:
1. Get new state:
   ```typescript
   const isInitialLoad = useChatStore((state) => state.isInitialLoad)
   ```

2. Update render logic:
   ```typescript
   // Show welcome only when no conversation selected AND no messages AND not initial load
   const showWelcome = !currentConversationId && messages.length === 0 && !isInitialLoad
   
   // Show loading only during initial load OR conversation-specific loading
   const showLoading = (isInitialLoad || isLoadingHistory) && messages.length === 0
   ```

**File**: `ui-new/src/hooks/useConversations.ts` (or wherever it's defined)

**Changes**:
1. On first load, set `isInitialLoad = true`
2. After conversations loaded, set `isInitialLoad = false`

### Testing
- ✅ App startup → Welcome screen shows (not loading spinner)
- ✅ Select conversation → Loading spinner shows
- ✅ Conversation loads → Messages show

---

## FIX 2: AI Message Deleted on Page Refresh

### Root Cause
- `messages` array not persisted in localStorage
- On page refresh, `currentConversationId` persists but `messages` is empty
- ChatArea doesn't reload messages because conversation didn't change
- Result: Empty messages array, no welcome screen

### Solution
Implement message hydration on app startup. When app loads and `currentConversationId` is set, reload messages from backend.

### Implementation

**File**: `ui-new/src/stores/chatStore.ts`

**Changes**:
1. Update persist config:
   ```typescript
   partialize: (state) => ({
       currentConversationId: state.currentConversationId,
       isSidebarOpen: state.isSidebarOpen,
       // Do NOT persist messages (they'll be hydrated)
   })
   ```

**File**: `ui-new/src/components/chat/ChatArea.tsx`

**Changes**:
1. Add hydration effect on mount:
   ```typescript
   useEffect(() => {
       // On app startup, if conversation is selected but no messages, load them
       if (currentConversationId && messages.length === 0 && !isLoadingHistory) {
           const hydrateMessages = async () => {
               try {
                   const freshMessages = await chatApi.getMessages(currentConversationId)
                   setMessages(freshMessages)
               } catch (error) {
                   console.error('[ChatArea] Hydration failed:', error)
               }
           }
           
           hydrateMessages()
       }
   }, [currentConversationId, messages.length, isLoadingHistory, setMessages])
   ```

2. Verify FAZE 4 metadata deep merge doesn't break message structure:
   - Check `app/memory/conversation.py` `update_message()` function
   - Ensure metadata merge preserves all fields
   - Test with image job metadata

### Testing
- ✅ Send message → AI responds
- ✅ Page refresh (F5) → AI message still there
- ✅ Multiple refreshes → Messages persist
- ✅ Image job metadata preserved after refresh

---

## FIX 3: Old Conversation Navigation

### Root Cause
- Race condition between conversation selection and message send
- `currentConversationId` might change between message creation and send
- OR: Sidebar selection doesn't properly guard against concurrent sends

### Solution
Capture conversation ID at message send time, use captured ID throughout send flow.

### Implementation

**File**: `ui-new/src/components/chat/ChatInput.tsx`

**Changes**:
1. Capture conversation ID at send time:
   ```typescript
   const handleSend = useCallback(async () => {
       if (!canSend) return
       
       const message = inputValue.trim()
       if (!message && attachments.length === 0) return
       
       setIsSending(true)
       setInputValue('')
       setShowToolbar(false)
       onClearReply?.()
       
       // ← CRITICAL: Capture conversation ID at send time
       const sendConversationId = currentConversationId
       
       console.log('[Chat] Sending message:', { 
           message, 
           sendConversationId,  // ← Use captured ID
           replyTo: replyTo?.id, 
           attachments: attachments.length 
       })
       
       try {
           // ... rest of send logic ...
           
           // Use sendConversationId instead of currentConversationId
           const response = await chatApi.sendMessage({
               message: textToSend,
               conversationId: sendConversationId,  // ← Use captured ID
               ...
           })
           
           // ... handle response ...
           
           // When creating new conversation, verify it matches captured ID
           const newConvId = response.headers.get('X-Conversation-ID')
           if (newConvId && !sendConversationId) {
               // Only update if we were creating new conversation
               useChatStore.setState((state) => ({
                   conversations: [newConversation, ...state.conversations],
                   currentConversationId: newConvId
               }))
           } else if (newConvId && sendConversationId && newConvId !== sendConversationId) {
               // ← GUARD: Backend returned different conversation ID
               console.error('[Chat] Conversation ID mismatch!', {
                   sent: sendConversationId,
                   received: newConvId
               })
               // Don't update store, keep using sent ID
           }
       } finally {
           setIsSending(false)
           stopStreaming()
       }
   }, [canSend, inputValue, attachments, currentConversationId, ...])
   ```

2. Add guard in Sidebar to prevent concurrent operations:
   ```typescript
   // Sidebar.tsx
   const handleSelectConversation = async (id: string) => {
       // Guard: Don't allow selection if already loading
       if (isLoadingHistory) {
           console.warn('[Sidebar] Already loading, ignoring selection')
           return
       }
       
       const store = useChatStore.getState()
       store.setLoadingHistory(true)
       setCurrentConversation(id)
       onItemSelect?.()
       
       try {
           const messages = await chatApi.getMessages(id)
           store.setMessages(messages)
           // ... refresh jobs ...
       } finally {
           store.setLoadingHistory(false)
       }
   }
   ```

### Testing
- ✅ Send message to Conversation A
- ✅ Quickly click Conversation B (before send completes)
- ✅ Message still goes to Conversation A
- ✅ Conversation B loads correctly
- ✅ No navigation to wrong conversation

---

## Implementation Order

1. **Fix 1 (Welcome Screen)** - 30 min
   - Lowest risk
   - No backend changes
   - Quick win

2. **Fix 2 (AI Message Deleted)** - 1 hour
   - Medium risk
   - Verify FAZE 4 metadata handling
   - Most critical for data integrity

3. **Fix 3 (Old Conversation)** - 45 min
   - Medium risk
   - Add guards and snapshots
   - Improves UX

---

## Testing Strategy

### Unit Tests
- Test each fix in isolation
- Mock API calls
- Verify state changes

### Integration Tests
- Test fixes together
- Verify no regressions
- Test edge cases

### Regression Tests
- Run all 57 existing tests
- Verify FAZE 4 still works
- Verify FAZE 1-3 still work

### Manual Testing
- Welcome screen on startup
- Message persistence on refresh
- Conversation navigation with concurrent operations

---

## Rollback Plan

If issues arise:
1. Revert chatStore.ts changes
2. Revert ChatArea.tsx changes
3. Revert ChatInput.tsx changes
4. Revert Sidebar.tsx changes

All changes are isolated and can be reverted independently.

---

## Success Criteria

- ✅ Welcome screen shows on startup
- ✅ AI messages persist after page refresh
- ✅ Conversation navigation works correctly
- ✅ All 57 existing tests pass
- ✅ 0 regressions
- ✅ No new issues introduced

