import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'

const REFRESH_MS = Number(import.meta.env.VITE_REFRESH_MS ?? 5000)

type Column = { column_name: string; data_type: string }

export default function App() {
  const [tables, setTables] = useState<string[]>([])
  const [columns, setColumns] = useState<Record<string, Column[]>>({})
  const [fks, setFks] = useState<any[]>([])
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [counts, setCounts] = useState<{ table: string; count: number }[]>([])
  const [preview, setPreview] = useState<any[]>([])
  const [previewCols, setPreviewCols] = useState<string[]>([])
  const [expandedTable, setExpandedTable] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [showPortal, setShowPortal] = useState(false)
  const [authMode, setAuthMode] = useState<'signup' | 'login'>('signup')
  const [authForm, setAuthForm] = useState({ email: '', password: '', fullName: '' })
  const [authMessage, setAuthMessage] = useState('')
  const [user, setUser] = useState<any>(null)
  const [resumeStatus, setResumeStatus] = useState('')
  const [resumeId, setResumeId] = useState<number | null>(null)
  const [resumeFileName, setResumeFileName] = useState('')
  const [jobs, setJobs] = useState<any[]>([])
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('')
  const [applyResult, setApplyResult] = useState<any>(null)
  const [applyError, setApplyError] = useState('')
  const cyRef = useRef<any>(null)
  const sidebarRef = useRef<HTMLDivElement | null>(null)
  const [graphHeight, setGraphHeight] = useState<number>(600)

  const rowLimit = 20
  const layoutOptions = useMemo(
    () => ({
      name: 'cose',
      animate: false,
      avoidOverlap: true,
      avoidOverlapPadding: 80,
      nodeSpacing: 70,
      spacingFactor: 2.4,
      gravity: 1.2,
      gravityRange: 600,
      cooling: 0.95,
      coolingFactor: 0.9,
      initialTemp: 1000,
      minTemp: 0.1,
      numIter: 2500,
      randomize: false,
      directed: true,
      tile: false,
    }),
    []
  )

  const fetchSchema = useCallback(async () => {
    const res = await fetch('/api/schema')
    if (!res.ok) return
    const json = await res.json()
    setTables(json.tables)
    setColumns(json.columns)
    setFks(json.fks)
    if (!selectedTable) setSelectedTable(json.tables[0] ?? null)
  }, [selectedTable])

  const fetchCounts = useCallback(async () => {
    const res = await fetch('/api/counts')
    if (!res.ok) return
    setCounts(await res.json())
  }, [])

  const fetchPreview = useCallback(async (table: string | null, limit: number) => {
    if (!table) return
    const res = await fetch(`/api/preview?table=${encodeURIComponent(table)}&limit=${limit}`)
    if (!res.ok) return
    const json = await res.json()
    setPreview(json.rows)
    setPreviewCols(json.columns)
  }, [])

  useEffect(() => {
    fetchSchema()
    fetchCounts()
    const id = setInterval(() => {
      fetchSchema()
      fetchCounts()
    }, REFRESH_MS)
    return () => clearInterval(id)
  }, [fetchSchema, fetchCounts])

  useEffect(() => {
    fetchPreview(selectedTable, rowLimit)
  }, [fetchPreview, selectedTable, rowLimit])

  const filteredStats = counts.filter((c) => c.table.toLowerCase().includes(searchTerm.toLowerCase()))

  const cytoStylesheet = [
    {
      selector: 'node',
      style: {
        content: 'data(label)',
        'text-wrap': 'wrap',
        'text-max-width': 220,
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '11px',
        'line-height': 1.3,
        'background-color': '#1e40af',
        color: '#ffffff',
        shape: 'ellipse',
        padding: '10px',
        width: '220px',
        height: '180px',
        'border-width': 2.5,
        'border-color': '#1e3a8a',
        'box-shadow': '0 10px 20px rgba(0,0,0,0.6)',
        'text-background-color': 'rgba(0,0,0,0.4)',
        'text-background-padding': '2px',
        'text-background-shape': 'round-rectangle',
      },
    },
    {
      selector: '.fk',
      style: {
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        label: 'data(label)',
        'font-size': '10px',
        'text-background-color': 'rgba(30,40,50,0.95)',
        'text-background-padding': '2px',
        'text-background-shape': 'round-rectangle',
        'line-color': '#10b981',
        'target-arrow-color': '#10b981',
        width: 2.5,
        'target-arrow-width': 13,
        'target-arrow-height': 13,
        color: '#d1fae5',
      },
    },
  ]

  const elements = [
    ...tables.map((t) => {
      const cols = columns[t] ?? []
      const displayCols = cols.slice(0, 6).map((c) => `${c.column_name}\n(${c.data_type})`).join('\n')
      const label = `${t}\n\n${displayCols}${cols.length > 6 ? '\n…' : ''}`.trim()
      return { data: { id: t, label }, classes: 'table' }
    }),
    ...fks.map((fk: any) => ({
      data: { source: fk.table_name, target: fk.foreign_table_name, label: `${fk.column_name}→${fk.foreign_column_name}` },
      classes: 'fk',
    })),
  ]

  useEffect(() => {
    if (!cyRef.current || elements.length === 0) return
    const cy = cyRef.current
    cy.layout(layoutOptions).run()
    cy.fit(undefined, 30)
    cy.zoom(cy.zoom() * 1.15)
  }, [elements.length, layoutOptions])

  useEffect(() => {
    const matchSidebarHeight = () => {
      const sidebarHeight = sidebarRef.current?.offsetHeight || 0
      if (sidebarHeight > 0 && sidebarHeight !== graphHeight) {
        setGraphHeight(sidebarHeight)
      }
    }
    matchSidebarHeight()
    window.addEventListener('resize', matchSidebarHeight)
    return () => window.removeEventListener('resize', matchSidebarHeight)
  }, [graphHeight, counts.length])

  useEffect(() => {
    if (!showPortal) return
    const loadJobs = async () => {
      try {
        const res = await fetch('/api/jobs')
        if (!res.ok) throw new Error('Failed to load jobs')
        setJobs(await res.json())
      } catch (err: any) {
        console.error(err)
      }
    }
    loadJobs()
  }, [showPortal])

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setAuthMessage('')
    const endpoint = authMode === 'signup' ? '/api/register' : '/api/login'
    const fd = new FormData()
    fd.append('email', authForm.email)
    fd.append('password', authForm.password)
    if (authMode === 'signup') {
      fd.append('full_name', authForm.fullName)
    }
    try {
      const res = await fetch(endpoint, { method: 'POST', body: fd })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Auth failed')
      setUser(json)
      setAuthMessage(authMode === 'signup' ? 'Account created. You are logged in.' : 'Logged in successfully.')
    } catch (err: any) {
      setAuthMessage(err.message)
    }
  }

  const handleResumeUpload = async (file: File | null) => {
    if (!user || !file) return
    setResumeStatus('Uploading...')
    setApplyResult(null)
    const fd = new FormData()
    fd.append('user_id', String(user.user_id))
    fd.append('file', file)
    try {
      const res = await fetch('/api/upload_resume', { method: 'POST', body: fd })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Upload failed')
      setResumeId(json.resume_id)
      setResumeFileName(json.file_name)
      setResumeStatus('Resume uploaded and parsed.')
    } catch (err: any) {
      setResumeStatus(err.message)
    }
  }

  const handleApply = async () => {
    if (!user) {
      setApplyError('Please log in first.')
      return
    }
    if (!resumeId) {
      setApplyError('Upload a resume first.')
      return
    }
    if (!selectedJobId) {
      setApplyError('Select a job.')
      return
    }
    setApplyError('')
    setApplyResult(null)
    const fd = new FormData()
    fd.append('user_id', String(user.user_id))
    fd.append('job_id', String(selectedJobId))
    fd.append('resume_id', String(resumeId))
    try {
      const res = await fetch('/api/apply', { method: 'POST', body: fd })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Application failed')
      setApplyResult({
        score: json.ngmi_score,
        comment: json.ngmi_comment,
        application_id: json.application_id,
      })
    } catch (err: any) {
      setApplyError(err.message)
    }
  }

  const renderPortal = () => (
    <div className="app-root portal-page">
      <header className="header">
        <div className="header-content portal-header">
          <div className="header-title">
            <h1>ngmiDBMS</h1>
            <p>Prove you&apos;re GMI: sign up, upload, pick a job, get scored.</p>
          </div>
          <button className="btn-reset" onClick={() => setShowPortal(false)}>
            ← Back to dashboard
          </button>
        </div>
      </header>

      <main className="portal-main portal-main-split">
        <section className="portal-card auth-card">
          <div className="auth-toggle">
            <button
              className={`toggle-btn ${authMode === 'signup' ? 'active' : ''}`}
              onClick={() => setAuthMode('signup')}
            >
              Sign Up
            </button>
            <button
              className={`toggle-btn ${authMode === 'login' ? 'active' : ''}`}
              onClick={() => setAuthMode('login')}
            >
              Log In
            </button>
          </div>
          <form className="auth-form" onSubmit={handleAuthSubmit}>
            <label>
              Email
              <input
                type="email"
                required
                value={authForm.email}
                onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
              />
            </label>
            {authMode === 'signup' && (
              <label>
                Full name
                <input
                  type="text"
                  required
                  value={authForm.fullName}
                  onChange={(e) => setAuthForm({ ...authForm, fullName: e.target.value })}
                />
              </label>
            )}
            <label>
              Password
              <input
                type="password"
                required
                value={authForm.password}
                onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
              />
            </label>
            <button type="submit" className="btn-primary btn-wide">
              {authMode === 'signup' ? 'Create account' : 'Log in'}
            </button>
            {authMessage && <div className="form-note">{authMessage}</div>}
            {user && <div className="form-note success">Signed in as {user.full_name}</div>}
            {!user && <div className="form-note">Sign up or log in to access your dashboard.</div>}
          </form>
        </section>

        <section className="portal-card dashboard-card">
          <div className="dashboard-header">
            <div>
              <h2>User dashboard</h2>
              <p>{user ? `Welcome, ${user.full_name || user.email}` : 'Unlock NGMI tools after signing in.'}</p>
            </div>
            <div className="pill">{user ? 'Signed in' : 'Locked'}</div>
          </div>

          <div className="dashboard-grid">
            <div className="portal-card upload-card nested-card">
              <div className="card-header">
                <div>
                  <h3>Upload resume (PDF)</h3>
                  <p>Select your latest resume to analyze.</p>
                </div>
                <div className="pill">{user ? user.email : 'Not signed in'}</div>
              </div>
              <div className="upload-box">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => handleResumeUpload(e.target.files?.[0] || null)}
                  disabled={!user}
                />
                <div className="upload-status">
                  {resumeStatus || 'Awaiting upload...'}
                  {resumeFileName && <span className="pill small">{resumeFileName}</span>}
                </div>
              </div>
            </div>

            <div className="portal-card job-card nested-card">
              <div className="card-header">
                <div>
                  <h3>Select a job</h3>
                  <p>Pick a posting to see if you are GMI.</p>
                </div>
                <div className="pill">{jobs.length} openings</div>
              </div>
              <div className="job-picker">
                <select
                  value={selectedJobId}
                  onChange={(e) => {
                    const val = e.target.value
                    setSelectedJobId(val ? Number(val) : '')
                  }}
                  disabled={!user || jobs.length === 0}
                >
                  <option value="">Choose a job</option>
                  {jobs.map((job) => (
                    <option key={job.job_id} value={job.job_id}>
                      {job.title} — {job.company}
                    </option>
                  ))}
                </select>
                <button className="btn-primary" onClick={handleApply} disabled={!user || !resumeId || !selectedJobId}>
                  Run NGMI check
                </button>
                {applyError && <div className="form-note">{applyError}</div>}
              </div>

              {applyResult && (
                <div className="result-card">
                  <div className="result-score">
                    <div className="score-label">NGMI score</div>
                    <div className="score-value">{applyResult.score ?? '—'}</div>
                    <div className="score-sub">Application #{applyResult.application_id}</div>
                  </div>
                  <div className="result-comment">
                    <div className="score-label">Commentary</div>
                    <p>{applyResult.comment || 'No feedback returned.'}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  )

  if (showPortal) {
    return renderPortal()
  }

  return (
    <div className="app-root">
      <header className="header">
        <div className="header-content">
          <div className="header-title">
            <h1>🗄️ ngmiDBMS</h1>
            <p>Interactive Database Schema Explorer</p>
          </div>
          <div className="header-controls">
            <input
              type="text"
              placeholder="🔍 Search tables..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            <select
              value={selectedTable ?? ''}
              onChange={(e) => setSelectedTable(e.target.value)}
              className="table-select"
            >
              <option value="">Select a table</option>
              {tables.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <button className="btn-reset" onClick={() => setShowPortal(true)}>
              Open NGMI portal
            </button>
          </div>
        </div>
      </header>

      <main className="main-container">
        <div className="graph-panel" style={{ minHeight: `${graphHeight}px`, height: `${graphHeight}px` }}>
          <div className="panel-header">
            <h2>📊 Schema Diagram</h2>
            <span className="badge">{tables.length} tables</span>
          </div>
          <CytoscapeComponent
            cy={(cy) => {
              cyRef.current = cy
            }}
            elements={elements}
            style={{ width: '100%', height: '100%' }}
            layout={layoutOptions}
            stylesheet={cytoStylesheet}
            wheelSensitivity={0.1}
            boxSelectionEnabled={false}
            autoungrabify={false}
            autolock={false}
            minZoom={0.1}
            maxZoom={3}
          />
        </div>

        <aside className="sidebar" ref={sidebarRef}>
          <div className="panel-header">
            <h2>📈 Table Statistics</h2>
            <span className="badge">{filteredStats.length}</span>
          </div>
          <div className="stats-grid">
            {filteredStats.map((c) => (
              <div
                key={c.table}
                className={`stat-card ${expandedTable === c.table ? 'expanded' : ''}`}
                onClick={() => {
                  setSelectedTable(c.table)
                  setExpandedTable(expandedTable === c.table ? null : c.table)
                }}
              >
                <div className="stat-header">
                  <h3>{c.table}</h3>
                  <span className="stat-count">{c.count.toLocaleString()}</span>
                </div>
                <div className="stat-label">rows</div>
                {expandedTable === c.table && (
                  <div className="stat-details">
                    <p>{columns[c.table]?.length ?? 0} columns</p>
                    <div className="column-list">
                      {columns[c.table]?.slice(0, 5).map((col) => (
                        <div key={col.column_name} className="column-item">
                          <span className="col-name">{col.column_name}</span>
                          <span className="col-type">{col.data_type}</span>
                        </div>
                      ))}
                      {(columns[c.table]?.length ?? 0) > 5 && (
                        <div className="col-more">+ {(columns[c.table]?.length ?? 0) - 5} more</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </aside>
      </main>

      <section className="preview-section">
        <div className="section-header">
          <h2>📋 Table Preview</h2>
          <div className="section-info">
            {selectedTable && <span className="info-badge">{selectedTable}</span>}
            <span className="info-badge secondary">
              {preview.length} / {rowLimit}
            </span>
          </div>
        </div>
        <div className="table-wrap">
          {preview.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>{previewCols.map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {preview.slice(0, rowLimit).map((row, i) => (
                  <tr key={i} className={i % 2 === 0 ? 'even' : 'odd'}>
                    {previewCols.map((col) => (
                      <td key={col}>{String(row[col] ?? '-').substring(0, 100)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">📭 No data available. Select a table to preview.</div>
          )}
        </div>
      </section>
    </div>
  )
}
