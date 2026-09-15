import { useEffect, useState } from "react";
import "./App.css";
import Auth from "./Auth";

const API_BASE = "http://localhost:8000/api";

/*
 * ---------------------------------------------------------
 * GET CSRF TOKEN FROM DJANGO COOKIE
 * ---------------------------------------------------------
 */
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


/*
 * ---------------------------------------------------------
 * COMMON HEADERS FOR DJANGO POST REQUESTS
 * ---------------------------------------------------------
 */
const getCSRFHeaders = () => {
  const csrfToken = getCSRFToken();

  return {
    "Content-Type": "application/json",
    "X-CSRFToken": csrfToken,
  };
};


function App() {
  const [user, setUser] = useState(null);

  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");

  const [reports, setReports] = useState([]);

  const [question, setQuestion] = useState("");
  const [assistantResult, setAssistantResult] = useState(null);

  const [reportResult, setReportResult] = useState(null);
  const [selectedReportId, setSelectedReportId] = useState("");

  const [selectedDepartment, setSelectedDepartment] = useState("");

  const [loadingDatasets, setLoadingDatasets] = useState(false);
  const [loadingReports, setLoadingReports] = useState(false);
  const [loadingAssistant, setLoadingAssistant] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");


  /*
   * ---------------------------------------------------------
   * LOAD DATASETS
   * ---------------------------------------------------------
   */
  const loadDatasets = async () => {
    setLoadingDatasets(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/datasets/`, {
        method: "GET",
        credentials: "include",
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error || "Unable to load datasets."
        );
      }

      const loadedDatasets = data.datasets || [];

      setDatasets(loadedDatasets);

      if (loadedDatasets.length > 0) {
        setSelectedDatasetId(
          String(loadedDatasets[0].id)
        );
      } else {
        setSelectedDatasetId("");
      }

    } catch (err) {
      setError(
        err.message || "Unable to load datasets."
      );
    } finally {
      setLoadingDatasets(false);
    }
  };


  /*
   * ---------------------------------------------------------
   * LOAD REPORTS
   * ---------------------------------------------------------
   */
  const loadReports = async () => {
    setLoadingReports(true);

    try {
      const response = await fetch(`${API_BASE}/reports/`, {
        method: "GET",
        credentials: "include",
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error || "Unable to load reports."
        );
      }

      setReports(data.reports || []);

    } catch (err) {
      setError(
        err.message || "Unable to load reports."
      );
    } finally {
      setLoadingReports(false);
    }
  };


  /*
   * ---------------------------------------------------------
   * LOAD DATA AFTER LOGIN
   * ---------------------------------------------------------
   */
  useEffect(() => {
    if (user) {
      loadDatasets();
      loadReports();
    }
  }, [user]);


  /*
   * ---------------------------------------------------------
   * LOGIN CALLBACK
   * ---------------------------------------------------------
   */
  const handleLogin = (loggedInUser) => {
    setUser(loggedInUser);
    setError("");
    setSuccessMessage("");
  };


  /*
   * ---------------------------------------------------------
   * LOGOUT
   * ---------------------------------------------------------
   */
  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/auth/logout/`, {
        method: "POST",
        credentials: "include",
        headers: getCSRFHeaders(),
      });

    } catch (err) {
      console.error("Logout error:", err);
    }

    setUser(null);
    setDatasets([]);
    setReports([]);
    setSelectedDatasetId("");
    setQuestion("");
    setAssistantResult(null);
    setReportResult(null);
    setSelectedReportId("");
    setError("");
    setSuccessMessage("");
  };


  /*
   * ---------------------------------------------------------
   * IMPORT HR DATASET
   * ---------------------------------------------------------
   */
  const importFile = async (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setUploading(true);
    setError("");
    setSuccessMessage("");

    const formData = new FormData();

    formData.append("file", file);

    try {
      const csrfToken = getCSRFToken();

      const response = await fetch(`${API_BASE}/import/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "X-CSRFToken": csrfToken,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error || "Unable to import the HR file."
        );
      }

      setSuccessMessage(
        data.message ||
          "HR dataset imported successfully."
      );

      await loadDatasets();

      event.target.value = "";

    } catch (err) {
      setError(
        err.message ||
          "Unable to import HR data."
      );
    } finally {
      setUploading(false);
    }
  };


  /*
   * ---------------------------------------------------------
   * SELECT DATASET
   * ---------------------------------------------------------
   */
  const handleDatasetChange = (event) => {
    setSelectedDatasetId(event.target.value);

    setAssistantResult(null);
    setReportResult(null);
    setError("");
  };


  /*
   * ---------------------------------------------------------
   * ASK AI ASSISTANT
   * ---------------------------------------------------------
   */
  const askAssistant = async () => {
    if (!question.trim()) {
      setError("Please enter an HR question.");
      return;
    }

    if (!selectedDatasetId) {
      setError(
        "Please select an HR dataset first."
      );
      return;
    }

    setLoadingAssistant(true);
    setError("");
    setSuccessMessage("");
    setAssistantResult(null);

    try {
      const csrfToken = getCSRFToken();

      const response = await fetch(
        `${API_BASE}/assistant/`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            question: question.trim(),
            dataset_id: Number(selectedDatasetId),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error ||
            "Unable to generate the HR report."
        );
      }

      setAssistantResult(data);

    } catch (err) {
      setError(
        err.message ||
          "Unable to communicate with the AI assistant."
      );
    } finally {
      setLoadingAssistant(false);
    }
  };


  /*
   * ---------------------------------------------------------
   * RUN SAVED REPORT
   * ---------------------------------------------------------
   */
  const runReport = async () => {
    if (!selectedReportId) {
      setError("Please select a report.");
      return;
    }

    if (!selectedDatasetId) {
      setError(
        "Please select a dataset first."
      );
      return;
    }

    const selectedReport = reports.find(
      (report) =>
        String(report.id) ===
        String(selectedReportId)
    );

    if (!selectedReport) {
      setError(
        "Selected report was not found."
      );
      return;
    }

    if (
      selectedReport.name ===
        "Department Employees" &&
      !selectedDepartment.trim()
    ) {
      setError(
        "Please enter a department name."
      );
      return;
    }

    setLoadingReport(true);
    setError("");
    setSuccessMessage("");
    setReportResult(null);

    try {
      const requestBody = {
        dataset_id: Number(selectedDatasetId),
      };

      if (
        selectedReport.name ===
        "Department Employees"
      ) {
        requestBody.department =
          selectedDepartment.trim();
      }

      const response = await fetch(
        `${API_BASE}/reports/${selectedReportId}/run/`,
        {
          method: "POST",
          credentials: "include",
          headers: getCSRFHeaders(),
          body: JSON.stringify(requestBody),
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error ||
            "Unable to run the report."
        );
      }

      setReportResult(data);

    } catch (err) {
      setError(
        err.message ||
          "Unable to run the selected report."
      );
    } finally {
      setLoadingReport(false);
    }
  };


  /*
   * ---------------------------------------------------------
   * SAMPLE QUESTIONS
   * ---------------------------------------------------------
   */
  const sampleQuestions = [
    "Show me all active employees",
    "How many employees are on leave?",
    "Which department has the most employees?",
    "Which job title has the fewest employees?",
    "Show me inactive employees",
    "Show me employees in the HR department",
  ];


  const useSampleQuestion = (sample) => {
    setQuestion(sample);
    setAssistantResult(null);
    setError("");
  };


  /*
   * ---------------------------------------------------------
   * CSV EXPORT
   * ---------------------------------------------------------
   */
  const exportCSV = (result) => {
    if (
      !result ||
      !result.results ||
      result.results.length === 0
    ) {
      setError(
        "There is no report data to export."
      );
      return;
    }

    const rows = result.results;

    const columns =
      result.columns &&
      result.columns.length > 0
        ? result.columns
        : Object.keys(rows[0]);


    const escapeCSV = (value) => {
      if (
        value === null ||
        value === undefined
      ) {
        return "";
      }

      const stringValue = String(value);

      if (
        stringValue.includes(",") ||
        stringValue.includes('"') ||
        stringValue.includes("\n")
      ) {
        return `"${stringValue.replace(
          /"/g,
          '""'
        )}"`;
      }

      return stringValue;
    };


    const csvRows = [];

    csvRows.push(
      columns
        .map(escapeCSV)
        .join(",")
    );


    rows.forEach((row) => {
      csvRows.push(
        columns
          .map((column) =>
            escapeCSV(row[column])
          )
          .join(",")
      );
    });


    const csvContent =
      csvRows.join("\n");


    const blob = new Blob(
      [csvContent],
      {
        type: "text/csv;charset=utf-8;",
      }
    );


    const url =
      URL.createObjectURL(blob);


    const link =
      document.createElement("a");

    link.href = url;
    link.download = "hr_report.csv";

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };


  /*
   * ---------------------------------------------------------
   * SELECTED DATASET
   * ---------------------------------------------------------
   */
  const selectedDataset =
    datasets.find(
      (dataset) =>
        String(dataset.id) ===
        String(selectedDatasetId)
    );


  /*
   * ---------------------------------------------------------
   * REPORT RESULT
   * ---------------------------------------------------------
   */
  const currentResult =
    reportResult || assistantResult;


  /*
   * ---------------------------------------------------------
   * LOGIN SCREEN
   * ---------------------------------------------------------
   */
  if (!user) {
    return (
      <Auth
        onLogin={handleLogin}
      />
    );
  }


  /*
   * ---------------------------------------------------------
   * DASHBOARD
   * ---------------------------------------------------------
   */
  return (
    <div className="app">

      {/* =====================================================
          HEADER
      ====================================================== */}
      <header className="topbar">

        <div className="brand-section">

          <div className="brand-logo">
            HR
          </div>

          <div>
            <h1>
              Intelligent HR
            </h1>

            <p>
              Reporting Assistant
            </p>
          </div>

        </div>


        <div className="user-section">

          <div className="user-info">

            <span className="user-label">
              Signed in as
            </span>

            <strong>
              {user.username}
            </strong>

          </div>


          <button
            className="logout-button"
            onClick={handleLogout}
          >
            Logout
          </button>

        </div>

      </header>


      {/* =====================================================
          MAIN CONTENT
      ====================================================== */}
      <main className="dashboard-container">

        {/* ===================================================
            PAGE INTRO
        ==================================================== */}
        <section className="welcome-section">

          <div>

            <span className="eyebrow">
              HR ANALYTICS
            </span>

            <h2>
              Your HR Dashboard
            </h2>

            <p>
              Ask questions about your HR data
              and generate reports using AI.
            </p>

          </div>

        </section>


        {/* ===================================================
            ALERTS
        ==================================================== */}
        {error && (
          <div className="alert error-alert">

            <span>⚠️</span>

            <span>
              {error}
            </span>

            <button
              onClick={() =>
                setError("")
              }
              className="alert-close"
            >
              ×
            </button>

          </div>
        )}


        {successMessage && (
          <div className="alert success-alert">

            <span>✅</span>

            <span>
              {successMessage}
            </span>

            <button
              onClick={() =>
                setSuccessMessage("")
              }
              className="alert-close"
            >
              ×
            </button>

          </div>
        )}


        {/* ===================================================
            FIRST-TIME USER / DATASET SECTION
        ==================================================== */}
        {datasets.length === 0 ? (

          <section className="empty-dataset-card">

            <div className="empty-dataset-icon">
              📊
            </div>

            <h2>
              Upload your HR dataset
            </h2>

            <p>
              You need to upload your HR
              employee data before you can
              generate reports.
            </p>


            <label className="primary-upload-button">

              {uploading
                ? "Uploading..."
                : "Upload HR File"}

              <input
                type="file"
                accept=".csv,.xlsx,.xls,.pdf"
                onChange={importFile}
                disabled={uploading}
                hidden
              />

            </label>


            <div className="supported-files">
              Supported formats:
              CSV, Excel and PDF
            </div>

          </section>

        ) : (

          <>

            {/* =================================================
                DATASET CARD
            ================================================== */}
            <section className="dashboard-card dataset-card">

              <div className="card-heading">

                <div>

                  <span className="card-kicker">
                    DATASET
                  </span>

                  <h3>
                    Your HR Data
                  </h3>

                  <p>
                    Select the dataset you want
                    to analyze.
                  </p>

                </div>


                <label className="secondary-upload-button">

                  {uploading
                    ? "Uploading..."
                    : "+ Upload New Dataset"}

                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls,.pdf"
                    onChange={importFile}
                    disabled={uploading}
                    hidden
                  />

                </label>

              </div>


              <div className="dataset-controls">

                <div className="dataset-select-wrapper">

                  <label htmlFor="dataset">
                    Select Dataset
                  </label>

                  <select
                    id="dataset"
                    value={selectedDatasetId}
                    onChange={
                      handleDatasetChange
                    }
                    disabled={
                      loadingDatasets
                    }
                  >

                    {datasets.map(
                      (dataset) => (
                        <option
                          key={dataset.id}
                          value={dataset.id}
                        >
                          {dataset.name}
                        </option>
                      )
                    )}

                  </select>

                </div>


                {selectedDataset && (
                  <div className="dataset-stats">

                    <div className="stat-box">

                      <span className="stat-icon">
                        👥
                      </span>

                      <div>

                        <span>
                          Total Employees
                        </span>

                        <strong>
                          {
                            selectedDataset.employee_count
                          }
                        </strong>

                      </div>

                    </div>


                    <div className="stat-box">

                      <span className="stat-icon">
                        📁
                      </span>

                      <div>

                        <span>
                          File Type
                        </span>

                        <strong>
                          {
                            selectedDataset.file_type ||
                            "HR Data"
                          }
                        </strong>

                      </div>

                    </div>

                  </div>
                )}

              </div>

            </section>


            {/* =================================================
                AI REPORT GENERATION
            ================================================== */}
            <section className="dashboard-card ai-card">

              <div className="card-heading">

                <div>

                  <span className="card-kicker">
                    AI REPORT GENERATION
                  </span>

                  <h3>
                    Ask your HR data
                  </h3>

                  <p>
                    Ask a question in natural
                    language and let the AI
                    generate the appropriate
                    HR report.
                  </p>

                </div>


                <div className="ai-badge">
                  AI
                </div>

              </div>


              <div className="question-area">

                <textarea
                  value={question}
                  onChange={(event) =>
                    setQuestion(
                      event.target.value
                    )
                  }
                  placeholder="Example: Which department has the most employees?"
                  rows={4}
                  disabled={
                    loadingAssistant
                  }
                />


                <button
                  className="generate-button"
                  onClick={
                    askAssistant
                  }
                  disabled={
                    loadingAssistant ||
                    !selectedDatasetId
                  }
                >

                  {loadingAssistant ? (
                    <>
                      <span className="spinner"></span>
                      Generating...
                    </>
                  ) : (
                    <>
                      Generate Report →
                    </>
                  )}

                </button>

              </div>


              {/* =================================================
                  SUGGESTED QUESTIONS
              ================================================== */}
              <div className="suggested-section">

                <div className="suggested-title">
                  Suggested Questions
                </div>


                <div className="question-chips">

                  {sampleQuestions.map(
                    (
                      sample,
                      index
                    ) => (
                      <button
                        key={index}
                        className="question-chip"
                        onClick={() =>
                          useSampleQuestion(
                            sample
                          )
                        }
                      >
                        {sample}
                      </button>
                    )
                  )}

                </div>

              </div>

            </section>


            {/* =================================================
                SAVED REPORTS
            ================================================== */}
            <section className="dashboard-card reports-card">

              <div className="card-heading">

                <div>

                  <span className="card-kicker">
                    REPORTS
                  </span>

                  <h3>
                    Generate a Report
                  </h3>

                  <p>
                    Run an existing HR report
                    against your selected dataset.
                  </p>

                </div>

              </div>


              {loadingReports ? (

                <div className="loading-state">
                  Loading reports...
                </div>

              ) : reports.length === 0 ? (

                <div className="empty-state">
                  No reports are currently
                  available.
                </div>

              ) : (

                <div className="report-controls">

                  <div className="report-select-wrapper">

                    <label htmlFor="report">
                      Report
                    </label>

                    <select
                      id="report"
                      value={
                        selectedReportId
                      }
                      onChange={(event) => {

                        setSelectedReportId(
                          event.target.value
                        );

                        setReportResult(null);
                        setError("");

                      }}
                    >

                      <option value="">
                        Select a report
                      </option>

                      {reports.map(
                        (report) => (
                          <option
                            key={report.id}
                            value={report.id}
                          >
                            {report.name}
                          </option>
                        )
                      )}

                    </select>

                  </div>


                  {selectedReportId &&
                    reports.find(
                      (report) =>
                        String(
                          report.id
                        ) ===
                        String(
                          selectedReportId
                        )
                    )?.name ===
                      "Department Employees" && (

                      <div className="report-select-wrapper">

                        <label htmlFor="department">
                          Department
                        </label>

                        <input
                          id="department"
                          type="text"
                          value={
                            selectedDepartment
                          }
                          onChange={(event) =>
                            setSelectedDepartment(
                              event.target.value
                            )
                          }
                          placeholder="Example: HR"
                        />

                      </div>
                    )}


                  <button
                    className="run-report-button"
                    onClick={
                      runReport
                    }
                    disabled={
                      loadingReport ||
                      !selectedReportId ||
                      !selectedDatasetId
                    }
                  >

                    {loadingReport
                      ? "Running..."
                      : "Run Report"}

                  </button>

                </div>

              )}

            </section>


            {/* =================================================
                YOUR REPORT
            ================================================== */}
            {currentResult && (
              <section className="dashboard-card results-card">

                <div className="results-header">

                  <div>

                    <span className="card-kicker">
                      YOUR REPORT
                    </span>

                    <h3>
                      {
                        currentResult.report ||
                        "AI Generated Report"
                      }
                    </h3>

                    <p>
                      {
                        currentResult.dataset
                          ?.name ||
                        selectedDataset?.name ||
                        "Selected HR dataset"
                      }
                    </p>

                  </div>


                  <button
                    className="export-button"
                    onClick={() =>
                      exportCSV(
                        currentResult
                      )
                    }
                  >
                    ↓ Export CSV
                  </button>

                </div>


                <div className="result-summary">

                  <div className="result-count">

                    <span>
                      Results
                    </span>

                    <strong>
                      {
                        currentResult.count ??
                        0
                      }
                    </strong>

                  </div>


                  {currentResult.source && (
                    <div className="result-source">

                      <span>
                        Generated by
                      </span>

                      <strong>
                        {
                          currentResult.source ===
                          "fast_sql"
                            ? "HR Query Engine"
                            : "AI Assistant"
                        }
                      </strong>

                    </div>
                  )}

                </div>


                {currentResult.results &&
                currentResult.results.length >
                  0 ? (

                  <div className="table-container">

                    <table>

                      <thead>

                        <tr>

                          {(
                            currentResult.columns ||
                            Object.keys(
                              currentResult
                                .results[0]
                            )
                          ).map(
                            (column) => (
                              <th
                                key={column}
                              >
                                {column}
                              </th>
                            )
                          )}

                        </tr>

                      </thead>


                      <tbody>

                        {currentResult.results.map(
                          (
                            row,
                            rowIndex
                          ) => (
                            <tr
                              key={
                                rowIndex
                              }
                            >

                              {(
                                currentResult.columns ||
                                Object.keys(
                                  row
                                )
                              ).map(
                                (column) => (
                                  <td
                                    key={
                                      column
                                    }
                                  >
                                    {
                                      row[
                                        column
                                      ] ===
                                        null ||
                                      row[
                                        column
                                      ] ===
                                        undefined
                                        ? "—"
                                        : String(
                                            row[
                                              column
                                            ]
                                          )
                                    }
                                  </td>
                                )
                              )}

                            </tr>
                          )
                        )}

                      </tbody>

                    </table>

                  </div>

                ) : (

                  <div className="no-results">
                    No records found for
                    this query.
                  </div>

                )}

              </section>
            )}

          </>

        )}

      </main>


      {/* =====================================================
          FOOTER
      ====================================================== */}
      <footer className="app-footer">

        <span>
          Intelligent HR Reporting Assistant
        </span>

        <span>
          Powered by Django • MySQL • Ollama Gemma 3
        </span>

      </footer>

    </div>
  );
}

export default App;