import { useState } from "react";

const API_BASE = "http://localhost:8000/api";


// =========================================================
// GET CSRF TOKEN FROM COOKIE
// =========================================================

const getCSRFToken = () => {

  const cookieName = "csrftoken=";

  const cookies = document.cookie.split(";");

  for (let cookie of cookies) {

    cookie = cookie.trim();

    if (cookie.startsWith(cookieName)) {

      return decodeURIComponent(
        cookie.substring(cookieName.length)
      );
    }
  }

  return "";
};


// =========================================================
// INITIALIZE CSRF
// =========================================================

const initializeCSRF = async () => {

  const response = await fetch(
    `${API_BASE}/auth/csrf/`,
    {
      method: "GET",
      credentials: "include",
    }
  );

  if (!response.ok) {
    throw new Error(
      "Unable to initialize security token."
    );
  }

  return response;
};


// =========================================================
// AUTH COMPONENT
// =========================================================

function Auth({ onLogin }) {

  const [isRegister, setIsRegister] =
    useState(false);

  const [username, setUsername] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");


  // =======================================================
  // LOGIN / REGISTER
  // =======================================================

  const handleSubmit = async (event) => {

    event.preventDefault();

    setError("");
    setSuccess("");


    // Username validation
    if (!username.trim()) {

      setError(
        "Username is required."
      );

      return;
    }


    // Password validation
    if (!password.trim()) {

      setError(
        "Password is required."
      );

      return;
    }


    setLoading(true);


    try {

      // ---------------------------------------------------
      // STEP 1: GET CSRF COOKIE
      // ---------------------------------------------------

      await initializeCSRF();


      // ---------------------------------------------------
      // STEP 2: READ CSRF TOKEN
      // ---------------------------------------------------

      const csrfToken =
        getCSRFToken();


      if (!csrfToken) {

        throw new Error(
          "CSRF token was not received from the server."
        );
      }


      // ---------------------------------------------------
      // STEP 3: SELECT ENDPOINT
      // ---------------------------------------------------

      const endpoint = isRegister
        ? `${API_BASE}/auth/register/`
        : `${API_BASE}/auth/login/`;


      // ---------------------------------------------------
      // STEP 4: SEND REQUEST
      // ---------------------------------------------------

      const response = await fetch(
        endpoint,
        {
          method: "POST",

          credentials: "include",

          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },

          body: JSON.stringify({

            username:
              username.trim(),

            password:
              password.trim(),

          }),
        }
      );


      // ---------------------------------------------------
      // STEP 5: READ RESPONSE
      // ---------------------------------------------------

      const data =
        await response.json();


      // ---------------------------------------------------
      // STEP 6: HANDLE ERROR
      // ---------------------------------------------------

      if (
        !response.ok ||
        !data.success
      ) {

        throw new Error(
          data.error ||
          "Authentication failed."
        );
      }


      // ---------------------------------------------------
      // STEP 7: SUCCESS
      // ---------------------------------------------------

      setSuccess(
        data.message ||
        "Login successful."
      );


      setPassword("");


      // Send logged-in user to App
      if (onLogin) {

        onLogin(
          data.user
        );
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

    setIsRegister(
      !isRegister
    );

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


        {/* =================================================
            LOGO
        ================================================== */}

        <div className="auth-logo">
          HR
        </div>


        {/* =================================================
            TITLE
        ================================================== */}

        <h1>
          Intelligent HR
        </h1>

        <p className="auth-subtitle">
          Reporting Assistant
        </p>


        {/* =================================================
            FORM TITLE
        ================================================== */}

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


        {/* =================================================
            ERROR
        ================================================== */}

        {error && (

          <div className="auth-alert auth-error">

            ⚠️ {error}

          </div>

        )}


        {/* =================================================
            SUCCESS
        ================================================== */}

        {success && (

          <div className="auth-alert auth-success">

            ✅ {success}

          </div>

        )}


        {/* =================================================
            FORM
        ================================================== */}

        <form
          onSubmit={handleSubmit}
        >


          {/* USERNAME */}

          <div className="form-group">

            <label htmlFor="username">
              Username
            </label>

            <input
              id="username"
              type="text"
              value={username}
              onChange={(event) =>
                setUsername(
                  event.target.value
                )
              }
              placeholder="Enter your username"
              autoComplete="username"
              disabled={loading}
            />

          </div>


          {/* PASSWORD */}

          <div className="form-group">

            <label htmlFor="password">
              Password
            </label>

            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
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


          {/* SUBMIT BUTTON */}

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


        {/* =================================================
            SWITCH LOGIN / REGISTER
        ================================================== */}

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