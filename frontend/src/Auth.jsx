import { useState } from "react";

const API_BASE =
  "https://intelligenthrreportingassistant.onrender.com/api";

// =========================================================
// GET CSRF TOKEN FROM SERVER RESPONSE
// =========================================================
const initializeCSRF = async () => {
  const response = await fetch(
    `${API_BASE}/auth/csrf/`,
    {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      "Unable to initialize security token."
    );
  }

  const data = await response.json();

  if (!data.csrfToken) {
    throw new Error(
      "CSRF token was not received from the server."
    );
  }

  return data.csrfToken;
};

// =========================================================
// AUTH COMPONENT
// =========================================================
function Auth({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // =======================================================
  // LOGIN / REGISTER
  // =======================================================
  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!username.trim()) {
      setError("Username is required.");
      return;
    }

    if (!password.trim()) {
      setError("Password is required.");
      return;
    }

    setLoading(true);

    try {
      // ---------------------------------------------------
      // STEP 1: GET CSRF TOKEN FROM SERVER
      // ---------------------------------------------------
      const csrfToken = await initializeCSRF();

      // ---------------------------------------------------
      // STEP 2: SELECT ENDPOINT
      // ---------------------------------------------------
      const endpoint = isRegister
        ? `${API_BASE}/auth/register/`
        : `${API_BASE}/auth/login/`;

      // ---------------------------------------------------
      // STEP 3: SEND REQUEST
      // ---------------------------------------------------
      const response = await fetch(
        endpoint,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            username: username.trim(),
            password: password.trim(),
          }),
        }
      );

      // ---------------------------------------------------
      // STEP 4: READ RESPONSE SAFELY
      // ---------------------------------------------------
      let data = {};

      const contentType =
        response.headers.get("content-type") || "";

      if (
        contentType.includes("application/json")
      ) {
        data = await response.json();
      } else {
        const text = await response.text();

        if (text) {
          data = {
            error: text,
          };
        }
      }

      // ---------------------------------------------------
      // STEP 5: HANDLE ERROR
      // ---------------------------------------------------
      if (
        !response.ok ||
        data.success === false
      ) {
        throw new Error(
          data.error ||
          data.detail ||
          "Authentication failed."
        );
      }

      // ---------------------------------------------------
      // STEP 6: SUCCESS
      // ---------------------------------------------------
      setSuccess(
        data.message ||
        (isRegister
          ? "Account created successfully."
          : "Login successful.")
      );

      setPassword("");

      if (onLogin && data.user) {
        onLogin(data.user);
      }

    } catch (err) {
      console.error(
        "Authentication error:",
        err
      );

      setError(
        err.message ||
        "Unable to connect to the server."
      );

    } finally {
      setLoading(false);
    }
  };

  // =======================================================
  // SWITCH LOGIN / REGISTER
  // =======================================================
  const switchMode = () => {
    setIsRegister(!isRegister);
    setUsername("");
    setPassword("");
    setError("");
    setSuccess("");
  };

  // =======================================================
  // UI
  // =======================================================
  return (
    <div className="auth-page">
      <div className="auth-card">

        <div className="auth-logo">
          HR
        </div>

        <h1>
          Intelligent HR
        </h1>

        <p className="auth-subtitle">
          Reporting Assistant
        </p>

        <h2>
          {isRegister
            ? "Create your account"
            : "Welcome back"}
        </h2>

        <p className="auth-description">
          {isRegister
            ? "Create an account to start analyzing your HR data."
            : "Sign in to access your HR reporting dashboard."}
        </p>

        {error && (
          <div className="auth-alert auth-error">
            ⚠️ {error}
          </div>
        )}

        {success && (
          <div className="auth-alert auth-success">
            ✅ {success}
          </div>
        )}

        <form onSubmit={handleSubmit}>

          <div className="form-group">
            <label htmlFor="username">
              Username
            </label>

            <input
              id="username"
              type="text"
              value={username}
              onChange={(event) =>
                setUsername(event.target.value)
              }
              placeholder="Enter your username"
              autoComplete="username"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">
              Password
            </label>

            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              placeholder="Enter your password"
              autoComplete={
                isRegister
                  ? "new-password"
                  : "current-password"
              }
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="auth-submit-button"
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : isRegister
                ? "Create Account"
                : "Login"}
          </button>

        </form>

        <div className="auth-switch">
          <span>
            {isRegister
              ? "Already have an account?"
              : "Don't have an account?"}
          </span>

          <button
            type="button"
            onClick={switchMode}
            disabled={loading}
          >
            {isRegister
              ? "Login"
              : "Create account"}
          </button>
        </div>

      </div>
    </div>
  );
}

export default Auth;