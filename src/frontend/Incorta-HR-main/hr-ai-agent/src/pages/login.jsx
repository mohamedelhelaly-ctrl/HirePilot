import AuthLayout from "../layouts/AuthLayout";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { GoogleOAuthProvider, useGoogleLogin } from "@react-oauth/google";
import * as authService from "../services/authService";

// Separate component to use Google Login hook within the provider context
function LoginForm() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Initialize Google Login with Authorization Code Flow
  const login = useGoogleLogin({
    onSuccess: async (codeResponse) => {
      setLoading(true);
      setError("");

      try {
        // codeResponse.code is the authorization code from Google
        const authCode = codeResponse.code;
        await authService.googleLogin(authCode);
        const user = authService.getUser();

        if (user.role === "hr_manager" || user.role === "hiring_manager") {
          navigate("/hr");
        } else {
          navigate("/");
        }
      } catch (err) {
        setError(err.message || "Login failed. Please try again.");
        console.error("Google login error:", err);
      } finally {
        setLoading(false);
      }
    },
    onError: () => {
      setError("Google login failed. Please try again.");
    },
    flow: "auth-code",
    scope: "openid email profile https://www.googleapis.com/auth/calendar",
  });

  return (
    <AuthLayout>
      <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[520px]">
        {/* Form side */}
        <div className="p-8 lg:p-12 flex flex-col justify-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted mb-2">
            Welcome back
          </p>
          <h2 className="text-2xl lg:text-3xl font-bold text-gray-900 mb-2">
            Sign in to your account
          </h2>
          <p className="text-muted mb-8">Access the Incorta AI HR Agent dashboard.</p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6 text-sm">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-6">
            <button
              onClick={() => login()}
              disabled={loading}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-white border-2 border-gray-200 rounded-xl hover:border-gray-300 hover:bg-gray-50 transition-colors font-medium text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              {loading ? "Signing in..." : "Sign in with Google"}
            </button>

            <div className="flex items-center gap-4">
              <div className="flex-1 border-t border-border" />
              <span className="text-muted text-sm">or</span>
              <div className="flex-1 border-t border-border" />
            </div>

            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
              <p className="text-brand-800 text-sm">
                <strong>Need an account?</strong>
                <br />
                Contact your HR Manager to be added to the system.
              </p>
            </div>
          </div>

          {loading && (
            <div className="mt-6 flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-muted text-sm">Signing in...</p>
            </div>
          )}
        </div>

        {/* Hero side */}
        <div className="relative hidden lg:flex flex-col justify-center p-12 bg-gradient-to-br from-brand-600 to-brand-800 text-white overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-white/10 -translate-y-1/2 translate-x-1/4" />
          <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-white/5 translate-y-1/3 -translate-x-1/4" />
          <div className="relative z-10">
            <img src="/favicon.svg" alt="" className="h-14 w-14 rounded-xl mb-6" />
            <h3 className="text-3xl font-bold mb-3 tracking-tight">Incorta HR</h3>
            <p className="text-blue-100 text-lg mb-6">AI Recruitment Assistant</p>
            <p className="text-blue-200/90 text-sm leading-relaxed max-w-sm">
              Screen, interview, and hire smarter with AI-powered candidate insights and
              conversational search across your talent pipeline.
            </p>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}

export default function Login() {
  const navigate = useNavigate();

  useEffect(() => {
    if (authService.isAuthenticated()) {
      navigate("/hr");
    }
  }, [navigate]);

  return (
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID || ""}>
      <LoginForm />
    </GoogleOAuthProvider>
  );
}
