/**
 * Profile — User identity, avatar, bio, password, and account management.
 * @module pages/Profile
 */
import { useEffect, useState, useRef } from 'react'
import { useClerk, useUser } from '@clerk/clerk-react'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { UpgradeModal } from '../components/billing/UpgradeModal'
import apiClient from '../lib/apiClient'
import toast from 'react-hot-toast'
import { useAuthStore, type AuthUser } from '../stores/authStore'
import { extractError } from '../lib/extractError'

export function Profile() {
  const { user, setUser, fetchUser, initials } = useAuthStore()
  const { user: clerkUser } = useUser()
  const [loading, setLoading] = useState(!user)

  // Profile form
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Avatar
  const fileRef = useRef<HTMLInputElement>(null)
  const [avatarUploading, setAvatarUploading] = useState(false)

  // Billing
  const [billingLoading, setBillingLoading] = useState(false)
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  // Stats
  const [projectCount, setProjectCount] = useState(0)

  useEffect(() => {
    const init = async () => {
      let u = user
      if (!u) {
        u = await fetchUser()
      }
      if (u) {
        const parts = (u.name || '').split(' ')
        setFirstName(parts[0] || '')
        setLastName(parts.slice(1).join(' ') || '')
        setDisplayName(u.display_name || '')
        setBio(u.bio || '')
      }
      setLoading(false)
    }
    init()
    apiClient.get('/projects').then(({ data }) => {
      setProjectCount(Array.isArray(data) ? data.length : 0)
    }).catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const fullName = [firstName.trim(), lastName.trim()].filter(Boolean).join(' ')
      const { data } = await apiClient.patch('/auth/me', {
        name: fullName || null,
        display_name: displayName.trim() || null,
        bio: bio.trim() || null,
      })
      setUser(data as AuthUser)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err: unknown) {
      toast.error(extractError(err, 'Failed to save profile.'))
    } finally {
      setSaving(false)
    }
  }

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setAvatarUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await apiClient.post('/auth/me/avatar', form)
      setUser(data as AuthUser)
      // Sync to Clerk so <UserButton /> in sidebar updates immediately
      if (clerkUser) {
        try {
          await clerkUser.setProfileImage({ file })
          await clerkUser.reload()
        } catch { /* non-blocking — Clerk sync is best-effort */ }
      }
    } catch (err: unknown) {
      toast.error(extractError(err, 'Failed to upload avatar.'))
    } finally {
      setAvatarUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleManageBilling = async () => {
    setBillingLoading(true)
    try {
      const { data } = await apiClient.post('/billing/portal', {
        return_url: window.location.href,
      })
      window.location.href = data.portal_url
    } catch (err: unknown) {
      toast.error(extractError(err, 'Failed to open billing portal.'))
    } finally {
      setBillingLoading(false)
    }
  }

  const { signOut } = useClerk()

  const handleLogout = () => {
    signOut({ redirectUrl: '/' })
  }
  const memberSince = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : '...'

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Profile" subtitle="Your account and public identity" />

        <div className="flex-1 p-4 md:p-6 overflow-y-auto pb-20 md:pb-6">
          <div className="max-w-2xl mx-auto space-y-6">
            {loading ? (
              <div className="text-center py-12 text-text-muted text-sm">Loading profile...</div>
            ) : (
              <>
                {/* ── Avatar + Identity ── */}
                <Card glow>
                  <div className="flex items-start gap-5">
                    <div className="relative group">
                      <div className="w-20 h-20 rounded-full bg-accent/20 border-2 border-accent/30 flex items-center justify-center text-2xl text-accent font-black shrink-0 overflow-hidden">
                        {user?.avatar_url ? (
                          <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
                        ) : (
                          initials()
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => fileRef.current?.click()}
                        disabled={avatarUploading}
                        className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs"
                      >
                        {avatarUploading ? '...' : 'Edit'}
                      </button>
                      <input
                        ref={fileRef}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        onChange={handleAvatarUpload}
                        className="hidden"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h2 className="text-lg font-bold text-white truncate">
                        {user?.display_name || user?.name || user?.email}
                      </h2>
                      <p className="text-sm text-text-muted truncate">{user?.email}</p>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent/10 border border-accent/20 text-accent capitalize">
                          {user?.account_type || 'free'} plan
                        </span>
                        {user?.email_verified && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400">
                            Verified
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>

                {/* ── Stats ── */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Projects', value: projectCount },
                    { label: 'Member Since', value: memberSince },
                    { label: 'Account', value: (user?.account_type || 'free').charAt(0).toUpperCase() + (user?.account_type || 'free').slice(1) },
                  ].map((stat) => (
                    <Card key={stat.label}>
                      <p className="text-lg font-bold text-white">{stat.value}</p>
                      <p className="text-[11px] text-text-muted">{stat.label}</p>
                    </Card>
                  ))}
                </div>

                {/* ── Subscription & Billing ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-3">Subscription & Billing</h3>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-white capitalize">{user?.account_type || 'free'} Plan</p>
                      <p className="text-xs text-text-muted mt-0.5">
                        {user?.account_type === 'pro'
                          ? 'Manage your subscription, payment method, and invoices'
                          : 'Upgrade to unlock more features'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {user?.account_type !== 'pro' && (
                        <Button size="sm" onClick={() => setUpgradeOpen(true)}>
                          Upgrade
                        </Button>
                      )}
                      {user?.account_type !== 'free' && (
                        <Button size="sm" variant="secondary" onClick={handleManageBilling} disabled={billingLoading}>
                          {billingLoading ? 'Opening...' : 'Manage Billing'}
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
                <UpgradeModal
                  open={upgradeOpen}
                  onClose={() => setUpgradeOpen(false)}
                  currentPlan={user?.account_type || 'free'}
                />

                {/* ── Edit Profile ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-4">Edit Profile</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                      <label className="block text-xs text-text-muted font-medium mb-1.5">First Name</label>
                      <input type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name"
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors" />
                    </div>
                    <div>
                      <label className="block text-xs text-text-muted font-medium mb-1.5">Last Name</label>
                      <input type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name"
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors" />
                    </div>
                    <div>
                      <label className="block text-xs text-text-muted font-medium mb-1.5">Display Name</label>
                      <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="How AI greets you"
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors" />
                    </div>
                  </div>
                  <div className="mb-4">
                    <label className="block text-xs text-text-muted font-medium mb-1.5">Bio</label>
                    <textarea value={bio} onChange={(e) => setBio(e.target.value)} placeholder="A short bio about yourself (optional)" maxLength={500} rows={3}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors resize-none" />
                    <p className="text-[10px] text-text-muted text-right mt-1">{bio.length}/500</p>
                  </div>
                  <Button size="sm" onClick={handleSave} disabled={saving}>
                    {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
                  </Button>
                </Card>

                {/* ── Account ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-3">Account</h3>
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-text-muted">
                      Member since {memberSince}
                    </p>
                    <Button variant="ghost" size="sm" onClick={handleLogout}>
                      Sign Out
                    </Button>
                  </div>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
