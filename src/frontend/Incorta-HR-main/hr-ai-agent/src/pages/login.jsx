import illustration from "../assets/logo-width.jpg";
import AuthLayout from "../layouts/AuthLayout";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { GoogleOAuthProvider, GoogleLogin } from "@react-oauth/google";
import * as authService from "../services/authService";

export default function Login() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Check if user is already authenticated
  useEffect(() => {
    if (authService.isAuthenticated()) {
      navigate("/hr");
    }
  }, [navigate]);

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError("");

    try {
      // Get the ID token from Google
      const idToken = credentialResponse.credential;

      // Send token to backend via authService
      const response = await authService.googleLogin(idToken);

      // Get user to determine role and navigate accordingly
      const user = authService.getUser();

      if (user.role === "hr_manager") {
        navigate("/hr");
      } else if (user.role === "hiring_manager") {
        navigate("/hiring-manager");
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
        <div className="flex w-full">
          {/* Left Image */}
          <div className="w-1/2 bg-white p-10 flex items-center justify-center">
            <img src={illustration} className="rounded-xl w-full h-full" />
          </div>

          {/* Right Form */}
          <div className="w-1/2 p-12 flex flex-col justify-center border-l border-gray-200">
            <h2 className="text-3xl font-bold mb-2">Sign in to your account</h2>
            <p className="text-gray-500 mb-8">Welcome to the AI HR Agent.</p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-6">
              {/* Google Login Button */}
              <div className="w-full flex justify-center">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  text="signin_with"
                  size="large"
                  locale="en"
                />
              </div>

              {/* Divider */}
              <div className="flex items-center gap-4">
                <div className="flex-1 border-t border-gray-300"></div>
                <span className="text-gray-500 text-sm">or</span>
                <div className="flex-1 border-t border-gray-300"></div>
              </div>

              {/* Info Box */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-blue-900 text-sm">
                  <strong>Need an account?</strong> <br />
                  Contact your HR Manager to be added to the system.
                </p>
              </div>
            </div>

            {/* Loading state */}
            {loading && (
              <div className="mt-4 text-center">
                <div className="inline-block">
                  <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <p className="text-gray-600 text-sm mt-2">Signing in...</p>
              </div>
            )}
          </div>
        </div>
      </AuthLayout>
    </GoogleOAuthProvider>
  );
}
