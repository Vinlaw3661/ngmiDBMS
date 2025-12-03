import { useMemo } from "react";

type StatCard = {
  label: string;
  value: string;
};

const mockStats: StatCard[] = [
  { label: "Jobs", value: "5" },
  { label: "Resumes", value: "0" },
  { label: "Applications", value: "0" }
];

function App() {
  const stats = useMemo(() => mockStats, []);

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">ngmiDBMS</p>
          <h1>Apply, score, iterate.</h1>
          <p className="subhead">
            React front-end placeholder. Wire this to the API once endpoints are ready.
          </p>
          <div className="cta-row">
            <button className="btn primary">Login</button>
            <button className="btn ghost">Register</button>
          </div>
        </div>
        <div className="stat-grid">
          {stats.map((stat) => (
            <div key={stat.label} className="card">
              <p className="muted">{stat.label}</p>
              <p className="value">{stat.value}</p>
            </div>
          ))}
        </div>
      </header>

      <section className="panel">
        <h2>Next steps</h2>
        <ol>
          <li>Add API client helpers (fetch/axios) in `src/api/`.</li>
          <li>Build pages: Login/Register, Resumes, Jobs, Applications.</li>
          <li>Wire to FastAPI/Flask endpoints that wrap existing services.</li>
        </ol>
      </section>
    </div>
  );
}

export default App;
