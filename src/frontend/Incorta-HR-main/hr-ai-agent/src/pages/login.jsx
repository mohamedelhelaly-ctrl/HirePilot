import AuthLayout from "../layouts/AuthLayout";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { GoogleOAuthProvider, GoogleLogin } from "@react-oauth/google";
import * as authService from "../services/authService";

export default function Login() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (authService.isAuthenticated()) {
      navigate("/hr");
    }
  }, [navigate]);

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError("");

    try {
      const idToken = credentialResponse.credential;
      await authService.googleLogin(idToken);
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
  };

  const handleGoogleError = () => {
    setError("Google login failed. Please try again.");
  };

  return (
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID || ""}>
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
              <div className="w-full flex justify-center lg:justify-start">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  text="signin_with"
                  size="large"
                  locale="en"
                />
              </div>

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
    </GoogleOAuthProvider>
  );
}
