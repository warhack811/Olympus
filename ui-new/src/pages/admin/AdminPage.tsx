
import { Routes, Route, Navigate } from 'react-router-dom'
import { AdminLayout } from '@/components/admin/layout/AdminLayout'
import { DashboardPage } from '@/pages/admin/dashboard/DashboardPage'
import { UsersPage } from '@/pages/admin/users/UsersPage'
import { AICorePage } from '@/pages/admin/ai-core/AICorePage'
import { CMSPage } from '@/pages/admin/cms/CMSPage'
import { KnowledgeBasePage } from '@/pages/admin/knowledge/KnowledgeBasePage'
import { SecurityLogsPage } from '@/pages/admin/security/SecurityLogsPage'
import { BroadcastPage } from '@/pages/admin/broadcast/BroadcastPage'
import { AnalyticsPage } from '@/pages/admin/analytics/AnalyticsPage'
import { SettingsPage } from '@/pages/admin/settings/SettingsPage'
import { BackupPage } from '@/pages/admin/backup/BackupPage'
import { FinOpsPage } from '@/pages/admin/finops/FinOpsPage'
import { AgentFactoryPage } from '@/pages/admin/agents/AgentFactoryPage'
import { RLHFPage } from '@/pages/admin/quality/RLHFPage'
import { APIGatewayPage } from '@/pages/admin/developer/APIGatewayPage'
import { PerformancePage } from '@/pages/admin/performance/PerformancePage'
import InvitesPage from '@/pages/admin/invites/InvitesPage'

export function AdminPage() {
    return (
        <Routes>
            <Route element={<AdminLayout />}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />

                {/* Placeholders for future modules */}
                <Route path="users/*" element={<UsersPage />} />
                <Route path="ai-core/*" element={<AICorePage />} />
                <Route path="knowledge/*" element={<KnowledgeBasePage />} />
                <Route path="cms/*" element={<CMSPage />} />
                <Route path="security/*" element={<SecurityLogsPage />} />
                <Route path="broadcast/*" element={<BroadcastPage />} />
                <Route path="analytics/*" element={<AnalyticsPage />} />
                <Route path="settings/*" element={<SettingsPage />} />

                <Route path="settings/*" element={<SettingsPage />} />
                <Route path="invites/*" element={<InvitesPage />} />

                {/* Enterprise Modules */}
                <Route path="backup/*" element={<BackupPage />} />
                <Route path="finops/*" element={<FinOpsPage />} />
                <Route path="agents/*" element={<AgentFactoryPage />} />
                <Route path="quality/*" element={<RLHFPage />} />
                <Route path="developer/*" element={<APIGatewayPage />} />
                <Route path="performance/*" element={<PerformancePage />} />

                <Route path="*" element={<Navigate to="dashboard" replace />} />
            </Route>
        </Routes>
    )
}
