import { useMemo, useState } from "react";

type StatCard = {
  label: string;
  value: string;
  tone?: "good" | "muted";
};

type Application = {
  application_id: number;
  applied_at: string;
  status: string;
  title: string;
  company: string;
  ngmi_score?: number | null;
  ngmi_comment?: string | null;
};

type NgmiDetail = {
  application_id: number;
  title: string;
  company: string;
  description: string;
  file_name: string;
  ngmi_score: number;
  ngmi_comment: string;
  generated_at: string;
};

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? value : dt.toLocaleString();
};

function App() {
  const [userId, setUserId] = useState("1");
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [ngmiDetail, setNgmiDetail] = useState<NgmiDetail | null>(null);
  const [loadingApps, setLoadingApps] = useState(false);
  const [loadingNgmi, setLoadingNgmi] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>("Load your applications to inspect their NGMI scores.");

  const averageScore = useMemo(() => {
    const scores = applications
      .map((app) => (typeof app.ngmi_score === "number" ? app.ngmi_score : null))
      .filter((score): score is number => score !== null);
    if (!scores.length) return null;
    const total = scores.reduce((sum, val) => sum + val, 0);
    return Number((total / scores.length).toFixed(1));
  }, [applications]);

  const readyScores = useMemo(
    () => applications.filter((app) => typeof app.ngmi_score === "number").length,
    [applications]
  );

  const stats = useMemo<StatCard[]>(
    () => [
      { label: "Applications", value: `${applications.length}` },
      { label: "NGMI scored", value: `${readyScores}`, tone: "good" },
      { label: "Avg. NGMI", value: averageScore !== null ? `${averageScore}` : "—", tone: "muted" }
    ],
    [applications.length, averageScore, readyScores]
  );

  const loadApplications = async () => {
    if (!userId.trim()) {
      setError("Enter a user ID to fetch applications.");
      return;
    }
    setLoadingApps(true);
    setError(null);
    setHint(null);
    setSelectedAppId(null);
    setNgmiDetail(null);

    try {
      const res = await fetch(`${API_BASE}/api/users/${userId}/applications`);
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload?.detail || "Unable to load applications.");
      }
      setApplications(payload as Application[]);
      setHint(
        payload.length
          ? "Select any application to see its NGMI score and reasoning."
          : "No applications yet for this user."
      );
    } catch (err) {
      setError((err as Error).message);
      setApplications([]);
    } finally {
      setLoadingApps(false);
    }
  };

  const loadNgmi = async (applicationId: number) => {
    setSelectedAppId(applicationId);
    setNgmiDetail(null);
    setLoadingNgmi(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/applications/${applicationId}/ngmi`);
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload?.detail || "Unable to load NGMI history.");
      }
      setNgmiDetail(payload as NgmiDetail);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoadingNgmi(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">ngmiDBMS</p>
          <h1>User dashboard</h1>
          <p className="subhead">
            Retrieve your applications and pull up NGMI scores whenever you need them.
          </p>
          <div className="cta-row">
            <label className="input-label">
              User ID
              <input
                type="text"
                className="input"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="e.g. 1"
              />
            </label>
            <button className="btn primary" onClick={loadApplications} disabled={loadingApps}>
              {loadingApps ? "Loading..." : "Load applications"}
            </button>
            <button className="btn ghost" onClick={loadApplications} disabled={loadingApps}>
              {loadingApps ? "Loading..." : "Past applications"}
            </button>
          </div>
          {error && <p className="error">{error}</p>}
          {!error && hint && <p className="muted small">{hint}</p>}
        </div>
        <div className="stat-grid">
          {stats.map((stat) => (
            <div key={stat.label} className="card">
              <p className="muted">{stat.label}</p>
              <p className={`value${stat.tone ? ` ${stat.tone}` : ""}`}>{stat.value}</p>
            </div>
          ))}
        </div>
      </header>

      <section className="panel">
        <div className="panel-header">
          <h2>Applications</h2>
          <span className="muted small">Fetches on demand so you only see what you ask for.</span>
        </div>
        {loadingApps ? (
          <p className="muted">Loading applications...</p>
        ) : applications.length ? (
          <div className="app-grid">
            {applications.map((app) => (
              <article
                key={app.application_id}
                className={`app-card${selectedAppId === app.application_id ? " active" : ""}`}
              >
                <div className="app-card__row">
                  <div>
                    <p className="muted">{app.company}</p>
                    <h3>{app.title}</h3>
                  </div>
                  <span className="pill">{app.status}</span>
                </div>
                <p className="muted small">Applied {formatDate(app.applied_at)}</p>
                <div className="score-row">
                  <span className="score-chip">
                    {typeof app.ngmi_score === "number" ? `NGMI ${app.ngmi_score}` : "Score pending"}
                  </span>
                  {app.ngmi_comment && <span className="muted small truncate">{app.ngmi_comment}</span>}
                </div>
                <button
                  className="btn ghost small"
                  onClick={() => loadNgmi(app.application_id)}
                  disabled={loadingNgmi && selectedAppId === app.application_id}
                >
                  {loadingNgmi && selectedAppId === app.application_id ? "Fetching..." : "View NGMI details"}
                </button>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p className="muted">No applications loaded yet. Enter a user ID and load to see results.</p>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>NGMI score</h2>
          <span className="muted small">Only shown after you request a specific application.</span>
        </div>
        {loadingNgmi ? (
          <p className="muted">Fetching NGMI details...</p>
        ) : ngmiDetail ? (
          <div className="ngmi-detail">
            <div className="ngmi-detail__header">
              <div>
                <p className="muted">Application {ngmiDetail.application_id}</p>
                <h3>
                  {ngmiDetail.title} @ {ngmiDetail.company}
                </h3>
              </div>
              <div className="ngmi-score">
                <span className="value good">{ngmiDetail.ngmi_score}</span>
                <span className="muted small">Generated {formatDate(ngmiDetail.generated_at)}</span>
              </div>
            </div>
            <div className="ngmi-body">
              <div className="ngmi-card">
                <p className="muted small">Resume file</p>
                <p>{ngmiDetail.file_name}</p>
              </div>
              <div className="ngmi-card">
                <p className="muted small">Commentary</p>
                <p className="justification">{ngmiDetail.ngmi_comment}</p>
              </div>
            </div>
            <div className="ngmi-card">
              <p className="muted small">Job description</p>
              <p className="muted small">{ngmiDetail.description}</p>
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <p className="muted">Pick an application above to reveal its NGMI analysis.</p>
          </div>
        )}
      </section>
    </div>
  );
}

export default App;
