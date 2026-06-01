/**
 * SignInPage — Clerk-managed sign-in with dark glassmorphism styling.
 * @module pages/SignInPage
 */
import { SignIn } from '@clerk/clerk-react'
import { PublicHeader } from '../components/layout/PublicHeader'

export function SignInPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <PublicHeader />
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <SignIn
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
          forceRedirectUrl="/home"
        />
      </div>
    </div>
  )
}
