/**
 * Admin — User management dashboard for admins.
 * Two tabs: Users (search + drawer + plan/override controls) and Audit Log.
 * Gates on user.is_admin; non-admins see an access-denied panel.
 * @module pages/Admin
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Card } from '../components/ui/Card'
import { AdminUserTable } from '../components/admin/AdminUserTable'
import { AdminUserDrawer } from '../components/admin/AdminUserDrawer'
import { AdminAuditList } from '../components/admin/AdminAuditList'
import { useAuthStore } from '../stores/authStore'

type Tab = 'users' | 'audit'

export function Admin() {
  const { user, loading, fetchUser } = useAuthStore()
  const [tab, setTab] = useState<Tab>('users')
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)

  // Ensure we have the latest user (and is_admin flag) on mount
  useEffect(() => {
    if (!user) {
      fetchUser()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Loading
  if (loading || !user) {
    return (
      <div className="min-h-screen bg-background flex">
        <Sidebar />
        <div className="ml-0 md:ml-[232px] flex-1 flex items-center justify-center h-dvh">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  // Not admin → friendly denial (not a silent redirect — admins lost on a
  // URL typo deserve to know they hit the gate)
  if (!user.is_admin) {
    return (
      <div className="min-h-screen bg-background flex">
        <Sidebar />
        <div className="ml-0 md:ml-[232px] flex-1 flex items-center justify-center h-dvh px-4">
          <Card className="max-w-md text-center">
            <h1 className="text-base font-semibold text-white mb-2">Admin access required</h1>
            <p className="text-sm text-text-muted mb-4">
              This page is only available to administrators. If you think you should have access,
              ask another admin to grant it.
            </p>
            <Link to="/home" className="text-accent text-sm hover:underline">
              Back to Home
            </Link>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Admin" subtitle="User management and audit log" />

        <div className="flex-1 p-4 md:p-6 overflow-y-auto">
          <div className="max-w-5xl mx-auto">
            {/* Tab bar */}
            <div className="flex gap-1 mb-5 border-b border-border">
              <button
                onClick={() => setTab('users')}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  tab === 'users'
                    ? 'border-accent text-accent'
                    : 'border-transparent text-text-muted hover:text-white'
                }`}
              >
                Users
              </button>
              <button
                onClick={() => setTab('audit')}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  tab === 'audit'
                    ? 'border-accent text-accent'
                    : 'border-transparent text-text-muted hover:text-white'
                }`}
              >
                Audit Log
              </button>
            </div>

            {tab === 'users' ? (
              <AdminUserTable onSelectUser={setSelectedUserId} />
            ) : (
              <AdminAuditList />
            )}
          </div>
        </div>
      </div>

      <AdminUserDrawer
        userId={selectedUserId}
        onClose={() => setSelectedUserId(null)}
      />
    </div>
  )
}
