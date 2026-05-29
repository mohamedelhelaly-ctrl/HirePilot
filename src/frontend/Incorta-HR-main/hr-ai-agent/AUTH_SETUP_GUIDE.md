# Authentication Setup Guide

This guide explains how to set up and use the new Google OAuth authentication system for the HR AI Agent frontend.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google OAuth Setup](#google-oauth-setup)
3. [Environment Configuration](#environment-configuration)
4. [Using the Auth Service](#using-the-auth-service)
5. [Protected Routes](#protected-routes)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Node.js v20.15.1 or higher
- npm v10.8.2 or higher
- Google Cloud Console account
- Backend API running at `http://127.0.0.1:8000`

### Installed Dependencies

- `@react-oauth/google` - Google OAuth integration
- `react-router-dom` - Client-side routing
- All other dependencies from `package.json`

---

## Google OAuth Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable the **Google+ API**

### Step 2: Create OAuth 2.0 Credentials

1. Go to **Credentials** in the left sidebar
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Choose **Web application**
4. Add authorized redirect URIs:
   - `http://localhost:5173` (Vite dev server)
   - `http://localhost:3000` (alternative port)
   - `http://127.0.0.1:5173`
   - Your production domain (e.g., `https://yourdomain.com`)
5. Click **Create**
6. Copy the **Client ID** (you'll need this next)

### Step 3: Configure Environment Variables

Create a `.env.local` file in the project root (`hr-ai-agent/`):

```env
# Google OAuth Client ID
VITE_GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com

# Backend API URL
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Replace `your_client_id_here` with your actual Google Client ID.

### Step 4: Verify Backend Setup

Ensure your backend is running and has:

1. **User Pre-registration**: Users must be pre-registered in the database
   - Use `/api/auth/setup` to create the first admin (HR manager)
   - Use `/api/auth/admin/users` to create additional users

2. **Correct CORS Settings**: Backend should accept requests from `http://localhost:5173`

3. **Google OAuth Verification**: Backend should verify Google ID tokens

---

## Environment Configuration

### Configuration Variables

```env
# Required
VITE_GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com

# Optional (defaults to http://127.0.0.1:8000/api)
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

### Development vs Production

**Development (.env.local):**
```env
VITE_GOOGLE_CLIENT_ID=dev_client_id.apps.googleusercontent.com
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

**Production (.env.production):**
```env
VITE_GOOGLE_CLIENT_ID=prod_client_id.apps.googleusercontent.com
VITE_API_BASE_URL=https://api.yourdomain.com
```

---

## Using the Auth Service

### Import the Service

```javascript
import * as authService from "../services/authService";
```

### Available Functions

#### 1. **Google Login**
```javascript
const response = await authService.googleLogin(idToken);
// Returns: { access_token, refresh_token, token_type }
```

#### 2. **Get Current User**
```javascript
const user = await authService.getCurrentUser();
// Returns: { id, email, full_name, role, is_active, created_at, updated_at }
```

#### 3. **Logout**
```javascript
await authService.logoutUser();
// Clears all tokens and user data
```

#### 4. **Token Management**
```javascript
// Check if authenticated
const isAuth = authService.isAuthenticated();

// Get access token
const token = authService.getAccessToken();

// Get user from storage
const user = authService.getUser();

// Get auth header for other API calls
const headers = authService.getAuthHeader();
```

#### 5. **Admin Functions** (HR Manager Only)

Create a new user:
```javascript
const newUser = await authService.createUser(
  "john@example.com",
  "John Doe",
  "hiring_manager"
);
```

#### 6. **System Setup** (One-time)

Initialize the system with first admin:
```javascript
const admin = await authService.setupSystem(
  "admin@example.com",
  "System Admin",
  "hr_manager"
);
```

---

## Protected Routes

### Creating a Protected Route Component

```javascript
import { Navigate } from "react-router-dom";
import * as authService from "../services/authService";

export default function ProtectedRoute({ children, requiredRole }) {
  const user = authService.getUser();
  const isAuth = authService.isAuthenticated();

  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/" replace />;
  }

  return children;
}
```

### Using in Router

```javascript
import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import Login from "./pages/login";
import HRHome from "./pages/hrHomePage";
import HiringManager from "./pages/hiringManagerDashboard";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/hr"
        element={
          <ProtectedRoute requiredRole="hr_manager">
            <HRHome />
          </ProtectedRoute>
        }
      />
      <Route
        path="/hiring-manager"
        element={
          <ProtectedRoute requiredRole="hiring_manager">
            <HiringManager />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

---

## Authentication Flow

### Login Flow

```
1. User clicks "Sign in with Google"
   ↓
2. Google OAuth dialog opens
   ↓
3. User authenticates with Google
   ↓
4. Frontend receives ID token from Google
   ↓
5. ID token sent to backend: POST /api/auth/google
   ↓
6. Backend verifies token and finds user by email
   ↓
7. Backend returns: { access_token, refresh_token }
   ↓
8. Frontend stores tokens in localStorage
   ↓
9. Frontend fetches user profile: GET /api/auth/me
   ↓
10. Frontend stores user info in localStorage
   ↓
11. User redirected to dashboard (/hr or /hiring-manager)
```

### Token Refresh Flow

When access token expires:

```
1. API request returns 401 Unauthorized
   ↓
2. authService automatically calls: POST /api/auth/refresh
   ↓
3. Backend validates refresh token and returns new access_token
   ↓
4. Frontend retries original request with new token
   ↓
5. Request succeeds or user is logged out
```

### Logout Flow

```
1. User clicks logout
   ↓
2. Frontend calls: POST /api/auth/logout
   ↓
3. Backend revokes refresh token(s)
   ↓
4. Frontend clears localStorage tokens
   ↓
5. User redirected to login page
```

---

## Common Use Cases

### Accessing Protected API Endpoints

```javascript
import * as authService from "../services/authService";

async function fetchUserCandidates() {
  try {
    const headers = authService.getAuthHeader();
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL}/candidates`,
      { headers }
    );
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Failed to fetch candidates:", error);
  }
}
```

### Redirecting Based on User Role

```javascript
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as authService from "../services/authService";

export default function Dashboard() {
  const navigate = useNavigate();
  const user = authService.getUser();

  useEffect(() => {
    if (!authService.isAuthenticated()) {
      navigate("/login");
    } else if (user?.role === "hr_manager") {
      navigate("/hr");
    } else if (user?.role === "hiring_manager") {
      navigate("/hiring-manager");
    }
  }, [navigate, user]);

  return <div>Loading...</div>;
}
```

### Adding Logout Button

```javascript
import * as authService from "../services/authService";
import { useNavigate } from "react-router-dom";

export default function NavBar() {
  const navigate = useNavigate();
  const user = authService.getUser();

  const handleLogout = async () => {
    try {
      await authService.logoutUser();
      navigate("/login");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <nav>
      <span>Welcome, {user?.full_name}</span>
      <button onClick={handleLogout}>Logout</button>
    </nav>
  );
}
```

---

## Troubleshooting

### Issue: "vite' is not recognized"

**Solution**: Run `npm install` in the `hr-ai-agent` directory.

```bash
cd hr-ai-agent
npm install
npm run dev
```

### Issue: Google Sign-In button not showing

**Solutions**:
1. Verify `VITE_GOOGLE_CLIENT_ID` is set in `.env.local`
2. Check that client ID is valid and not expired
3. Verify `http://localhost:5173` is in authorized redirect URIs
4. Clear browser cache and refresh

### Issue: "User not found" error on login

**Solution**: User must be pre-registered in the database:
1. Ask HR manager to create your account using `/api/auth/admin/users`
2. Or run system setup first: `POST /api/auth/setup`

### Issue: CORS errors

**Solution**: Backend needs to allow requests from frontend origin:

Add to backend `main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: Tokens not persisting between page reloads

**Solution**: Tokens are stored in `localStorage`. Check:
1. Browser localStorage is enabled
2. No privacy mode (incognito) which clears storage
3. Check DevTools → Application → Local Storage

### Issue: "Invalid ID token" error

**Possible causes**:
1. Client ID mismatch between frontend and backend
2. Token expired (takes a few minutes)
3. Backend can't reach Google to verify token

**Solution**:
1. Verify Client ID in `.env.local`
2. Check backend logs for verification errors
3. Ensure backend has internet access

---

## Security Notes

✅ **Best Practices Implemented**:
- Tokens stored in localStorage (accessible only to JavaScript)
- Access tokens auto-refresh before expiration
- Refresh tokens can be revoked on logout
- Bearer token validation on all protected endpoints
- Role-based access control (RBAC)

⚠️ **Additional Security Considerations**:
1. Use HTTPS in production (not HTTP)
2. Set `Secure` flag on cookies for sensitive data
3. Implement refresh token rotation
4. Add CSRF protection
5. Implement rate limiting on auth endpoints
6. Use `httpOnly` cookies for refresh tokens (backend feature)

---

## Next Steps

1. ✅ Create `.env.local` with Google Client ID
2. ✅ Create first admin user with `/api/auth/setup`
3. ✅ Test login with Google OAuth
4. ✅ Create additional users with `/api/auth/admin/users`
5. ✅ Implement protected routes in your app
6. ✅ Add logout button to navigation
7. ✅ Test token refresh flow

---

## API Endpoint Reference

All endpoints require the header:
```
Authorization: Bearer {access_token}
```

(except `/auth/google`, `/auth/setup`, and `/auth/refresh`)

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/auth/google` | ❌ | Google OAuth login |
| POST | `/auth/refresh` | ❌ | Refresh access token |
| GET | `/auth/me` | ✅ | Get current user |
| POST | `/auth/logout` | ✅ | Logout user |
| POST | `/auth/admin/users` | ✅ HR | Create new user |
| POST | `/auth/setup` | ❌ | Initialize system (once) |

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: `tail -f /path/to/backend.log`
3. Check browser console: Press F12 → Console
4. Review Network tab for API responses

