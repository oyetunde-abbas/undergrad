import { useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const PAGE_LIMIT = 20
const LOGO_DATA_URI = "data:image/png;base64,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"

const WORK_STYLE_CHIPS = [
  { label: '⚡ For you', remote: null },
  { label: 'On-site', remote: false },
  { label: 'Remote', remote: true },
]

const TYPE_CHIPS = ['Internship', 'SIWES', 'Graduate Program', 'Full-time', 'Part-time', 'Contract']

function initials(name) {
  if (!name) return '?'
  return name.trim().charAt(0).toUpperCase()
}

// Placeholder "match score" until a real recommendation model exists.
function fakeMatchScore(job) {
  const base = 78
  const bonus = (job.id % 19)
  return Math.min(97, base + bonus)
}

function JobTags({ job }) {
  const tags = []
  if (job.type) tags.push({ label: job.type, cls: '' })
  if (job.remote === 1) tags.push({ label: 'Remote', cls: 'orange' })
  if (job.experience_level) tags.push({ label: job.experience_level, cls: 'teal' })
  if (tags.length === 0) return null
  return (
    <div className="job-tags">
      {tags.map((t, i) => <div key={i} className={`job-tag ${t.cls}`}>{t.label}</div>)}
    </div>
  )
}

function MiniJobCard({ job, isSaved, onToggleSave, onOpen }) {
  const match = fakeMatchScore(job)
  const tag = job.type || (job.remote === 1 ? 'Remote' : null) || job.experience_level
  return (
    <div className="mini-card" onClick={() => onOpen(job)}>
      <div className="mini-card-title">{job.title}</div>
      <div className="mini-card-top">
        <div className="mini-card-logo">{initials(job.company)}</div>
        <div
          className={`mini-bookmark ${isSaved ? 'saved' : ''}`}
          onClick={(e) => { e.stopPropagation(); onToggleSave(job) }}
        >
          {isSaved ? '★' : '☆'}
        </div>
      </div>
      <div className="mini-card-company">{job.company}</div>
      <div className="mini-card-meta">{job.location || 'Location not specified'}</div>
      {tag && <div className="mini-card-tag">{tag}</div>}
      <div className="mini-card-match">
        <span className="mini-match-icon">◎</span> {match}% Match
      </div>
    </div>
  )
}

function BottomNav({ active, onNavigate }) {
  return (
    <div className="navbar">
      <button className={`nav-item ${active === 'dashboard' ? 'active' : ''}`} onClick={() => onNavigate('dashboard')}>
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
        Dashboard
      </button>
      <button className={`nav-item ${active === 'explore' ? 'active' : ''}`} onClick={() => onNavigate('explore')}>
        <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        Explore
      </button>
      <button className="nav-item fab" onClick={() => onNavigate('applications')}>
        <div className="fab-circle">
          <svg viewBox="0 0 24 24"><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M4 7h16v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7z"/></svg>
        </div>
      </button>
      <button className={`nav-item ${active === 'saved' ? 'active' : ''}`} onClick={() => onNavigate('saved')}>
        <svg viewBox="0 0 24 24"><path d="M6 3h12v18l-6-4.5L6 21V3z"/></svg>
        Saved
      </button>
      <button className={`nav-item ${active === 'profile' ? 'active' : ''}`} onClick={() => onNavigate('profile')}>
        <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg>
        Profile
      </button>
    </div>
  )
}

function JobCard({ job, featured, isSaved, onToggleSave, onOpen }) {
  const metaParts = [job.company, job.location, job.remote === 1 ? 'Remote' : null].filter(Boolean)

  if (featured) {
    const match = fakeMatchScore(job)
    return (
      <div className="featured-card">
        <div className="job-top">
          <div className="job-logo" onClick={() => onOpen(job)} style={{ cursor: 'pointer' }}>{initials(job.company)}</div>
          <div className="job-info job-title-link" onClick={() => onOpen(job)}>
            <div className="job-title">{job.title}</div>
            <div className="job-meta">{metaParts.join(' · ') || 'Location not specified'}</div>
          </div>
          <div className={`bookmark ${isSaved ? 'saved' : ''}`} onClick={() => onToggleSave(job)}>
            {isSaved ? '♥' : '♡'}
          </div>
        </div>
        <JobTags job={job} />
        <div className="match-box">
          <div className="match-icon">⚡</div>
          <div className="match-text">
            <div className="match-pct">Estimated match</div>
            <div className="match-sub">Based on this listing's tags and level</div>
          </div>
          <div className="match-pill">{match}%</div>
        </div>
        <div className="match-bar-track"><div className="match-bar-fill" style={{ width: `${match}%` }} /></div>
        <button className="job-cta" onClick={() => onOpen(job)}>
          View Opportunity →
        </button>
      </div>
    )
  }

  return (
    <div className="job-card">
      <div className="job-top">
        <div className="job-logo" onClick={() => onOpen(job)} style={{ cursor: 'pointer' }}>{initials(job.company)}</div>
        <div className="job-info job-title-link" onClick={() => onOpen(job)}>
          <div className="job-title">{job.title}</div>
          <div className="job-meta">{metaParts.join(' · ') || 'Location not specified'}</div>
        </div>
        <div className={`bookmark ${isSaved ? 'saved' : ''}`} onClick={() => onToggleSave(job)}>
          {isSaved ? '♥' : '♡'}
        </div>
      </div>
      <JobTags job={job} />
      <button className="job-cta" onClick={() => onOpen(job)}>
        View opportunity →
      </button>
    </div>
  )
}

function JobDetailPage({ job, isSaved, onToggleSave, onBack, onNavigate }) {
  const metaParts = [job.company, job.location, job.remote === 1 ? 'Remote' : null].filter(Boolean)

  return (
    <div className="app">
      <div className="subpage-header">
        <button className="back-btn" onClick={onBack}>←</button>
        <div className="subpage-title">Opportunity</div>
      </div>

      <div className="detail-hero">
        <div className="detail-logo">{initials(job.company)}</div>
        <div className="detail-title">{job.title}</div>
        <div className="detail-company">{metaParts.join(' · ')}</div>
        <div className="detail-meta-row"><JobTags job={job} /></div>
      </div>

      <div className="detail-summary">
        <h3>About this listing</h3>
        <p style={{ whiteSpace: 'pre-line' }}>{job.summary ? job.summary.replace(/<[^>]+>/g, '') : 'No description provided by the source.'}</p>
      </div>

      <div className="detail-source-note">
        Source: {job.source || 'unknown'} · Added {job.created_at ? new Date(job.created_at).toLocaleDateString() : 'recently'}
      </div>

      <div className="detail-cta-wrap">
        <div className={`detail-save-btn ${isSaved ? 'saved' : ''}`} onClick={() => onToggleSave(job)}>
          {isSaved ? '♥' : '♡'}
        </div>
        <a className="detail-apply-btn" href={job.apply_url} target="_blank" rel="noopener noreferrer">
          Apply Now →
        </a>
      </div>

      <div className="bottom-pad" />
      <BottomNav active="explore" onNavigate={onNavigate} />
    </div>
  )
}

function SavedPage({ savedJobs, loadError, onToggleSave, onOpen, onBack, onNavigate }) {
  const list = Object.values(savedJobs)
  return (
    <div className="app">
      <div className="subpage-header">
        <button className="back-btn" onClick={onBack}>←</button>
        <div className="subpage-title">Saved Opportunities</div>
      </div>

      {loadError ? (
        <div className="state-msg error">
          Couldn't load your saved jobs — check that the backend at {API_BASE} is running.
        </div>
      ) : list.length === 0 ? (
        <div className="saved-empty">
          <div className="saved-empty-icon">🔖</div>
          <h3>Nothing saved yet</h3>
          <p>Tap the bookmark icon on any listing to save it here.</p>
        </div>
      ) : (
        <div className="section" style={{ paddingTop: 4 }}>
          <div className="job-list">
            {list.map((job) => (
              <JobCard key={job.id} job={job} isSaved={true} onToggleSave={onToggleSave} onOpen={onOpen} />
            ))}
          </div>
        </div>
      )}

      <div className="bottom-pad" />
      <BottomNav active="saved" onNavigate={onNavigate} />
    </div>
  )
}

function FiltersModal({
  workStyleIdx, setWorkStyleIdx,
  activeType, setActiveType,
  activeLocation, setActiveLocation,
  locations,
  onClose, onReset, resultCount
}) {
  return (
    <div className="filters-backdrop" onClick={onClose}>
      <div className="filters-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="filters-head">
          <h3>Filters</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <button className="filters-reset" onClick={onReset}>Reset</button>
            <button className="filters-close" onClick={onClose}>✕</button>
          </div>
        </div>

        <div className="filters-group">
          <div className="filters-group-label">Work style</div>
          <div className="filters-chip-grid">
            {WORK_STYLE_CHIPS.map((c, i) => (
              <button key={c.label} className={`chip ${i === workStyleIdx ? 'active' : ''}`} onClick={() => setWorkStyleIdx(i)}>
                {c.label}
              </button>
            ))}
          </div>
        </div>

        <div className="filters-group">
          <div className="filters-group-label">Type</div>
          <div className="filters-chip-grid">
            <button className={`chip ${activeType === '' ? 'active' : ''}`} onClick={() => setActiveType('')}>Any</button>
            {TYPE_CHIPS.map((t) => (
              <button key={t} className={`chip ${activeType === t ? 'active' : ''}`} onClick={() => setActiveType(activeType === t ? '' : t)}>
                {t}
              </button>
            ))}
          </div>
          <div className="filters-note">
            "Internship," "Full-time," "Part-time," and "Contract" are tagged from each listing's actual title/description. "SIWES" and "Graduate Program" are Nigeria-specific and will return 0 results for now — the current sources (Adzuna, RemoteOK, etc.) don't carry that data; that's what the 3MTT/HNG/Decagon scraping phase is for.
          </div>
        </div>

        <div className="filters-group">
          <div className="filters-group-label">Location</div>
          <div className="filters-chip-grid">
            <button className={`chip ${activeLocation === '' ? 'active' : ''}`} onClick={() => setActiveLocation('')}>Any location</button>
            {locations.slice(0, 12).map((loc) => (
              <button key={loc} className={`chip ${activeLocation === loc ? 'active' : ''}`} onClick={() => setActiveLocation(activeLocation === loc ? '' : loc)}>
                {loc}
              </button>
            ))}
          </div>
        </div>

        <div className="filters-footer">
          <button className="filters-apply-btn" onClick={onClose}>
            Show {resultCount} results
          </button>
        </div>
      </div>
    </div>
  )
}

const POPULAR_SEARCHES = ['⚡ For you', 'Software Engineer', 'Data Analyst', 'Product Manager']

function ProgressRing({ pct, size = 108 }) {
  const angle = Math.round((pct / 100) * 360)
  return (
    <div
      className="progress-ring"
      style={{
        width: size, height: size,
        background: `conic-gradient(var(--lime) ${angle}deg, rgba(255,255,255,0.07) ${angle}deg)`,
      }}
    >
      <div className="progress-ring-inner">
        <div className="progress-ring-pct">{pct}%</div>
        <div className="progress-ring-label">Strong</div>
      </div>
    </div>
  )
}

const StatIcon = {
  briefcase: <svg viewBox="0 0 24 24"><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M4 7h16v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7z" /></svg>,
  chat: <svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" /></svg>,
  check: <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.3 2.3 4.7-4.8" /></svg>,
  bookmark: <svg viewBox="0 0 24 24"><path d="M6 3h12v18l-6-4.5L6 21V3z" /></svg>,
}

// Placeholder activity trend for the design pass — will be wired to a real
// analytics/events table once the backend tracks activity over time.
const ACTIVITY_TREND = [4, 6, 5, 9, 7, 15, 12]
const ACTIVITY_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function ActivityChart({ data, days }) {
  const w = 320, h = 130, padL = 26, padB = 20, padT = 14
  const max = Math.max(...data, 20)
  const stepX = (w - padL) / (data.length - 1)
  const points = data.map((v, i) => {
    const x = padL + i * stepX
    const y = padT + (1 - v / max) * (h - padT - padB)
    return [x, y]
  })
  const linePath = points.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(' ')
  const areaPath = `${linePath} L${points[points.length - 1][0]},${h - padB} L${points[0][0]},${h - padB} Z`
  const peakIdx = data.indexOf(Math.max(...data))
  const peak = points[peakIdx]
  const gridVals = [0, 5, 10, 15, 20].filter((g) => g <= max)

  return (
    <svg viewBox={`0 0 ${w} ${h + 18}`} className="activity-svg">
      <defs>
        <linearGradient id="actFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--violet)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--violet)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {gridVals.map((g) => {
        const y = padT + (1 - g / max) * (h - padT - padB)
        return (
          <g key={g}>
            <line x1={padL} x2={w} y1={y} y2={y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
            <text x="0" y={y + 3} fontSize="8" fill="var(--muted-2)">{g}</text>
          </g>
        )
      })}
      <path d={areaPath} fill="url(#actFill)" />
      <path d={linePath} fill="none" stroke="var(--violet)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={peak[0]} cy={peak[1]} r="4" fill="var(--lime)" stroke="var(--bg)" strokeWidth="2" />
      {days.map((d, i) => (
        <text key={d} x={padL + i * stepX} y={h + 14} fontSize="8" fill="var(--muted-2)" textAnchor="middle">{d}</text>
      ))}
    </svg>
  )
}

function DashboardPage({ userName, jobs, savedJobs, applications, onToggleSave, onOpen, onGoExplore, onGoApplications, onGoSaved, onGoProfile, onNavigate }) {
  const recommended = jobs.slice(0, 4)
  const savedCount = Object.keys(savedJobs).length
  const active = applications.filter((a) => a.status !== 'Archived').length
  const interviews = applications.filter((a) => a.status === 'Interview').length
  const offers = applications.filter((a) => a.status === 'Offer').length

  const checklist = [
    { label: 'Basic info', done: true },
    { label: 'About me', done: true },
    { label: 'Skills', done: true },
    { label: 'Experience', done: true },
    { label: 'Resume', done: false },
  ]
  const strength = Math.round((checklist.filter((c) => c.done).length / checklist.length) * 100)

  const missionGoal = 3
  const missionProgress = Math.min(active, missionGoal)
  const activityPeak = Math.max(...ACTIVITY_TREND)

  return (
    <div className="app">
      <div className="header">
        <div className="header-left">
          <img src={LOGO_DATA_URI} className="logo-mark" alt="Undergrad U" />
          <span className="wordmark">under<b>grad</b></span>
        </div>
        <div className="bell">🔔</div>
      </div>

      <div className="dash-hero">
        <div className="dash-hero-text">
          <div className="dash-hero-greeting">Good morning, <b>{userName}</b> 👋</div>
          <h1>Make progress.<br />Create <b>opportunities.</b></h1>
          <p>Track your journey and stay ready for the right role.</p>
        </div>
        <div className="dash-hero-glow">
          <div className="dash-hero-ring r1" />
          <div className="dash-hero-ring r2" />
          <img src={LOGO_DATA_URI} className="dash-hero-logo" alt="" />
        </div>
      </div>

      <div className="mission-row">
        <div className="mission-card">
          <div className="mission-label">⚡ TODAY'S GOAL</div>
          <h3>Apply to {missionGoal} new jobs</h3>
          <p>{missionProgress >= missionGoal ? "Goal reached — nice work." : "Keep going, you've got this."}</p>
          <div className="mission-steps">
            {Array.from({ length: missionGoal }).map((_, i) => (
              <div key={i} className={`mission-step ${i < missionProgress ? 'done' : ''}`}>
                {i < missionProgress ? '✓' : i + 1}
              </div>
            ))}
          </div>
          <div className="mission-bar-track"><div className="mission-bar-fill" style={{ width: `${(missionProgress / missionGoal) * 100}%` }} /></div>
          <div className="mission-count">{missionProgress} / {missionGoal} completed</div>
        </div>
        <div className="mission-side">
          <div className="mission-side-icon">🔥</div>
          <div className="mission-side-num">7</div>
          <div className="mission-side-label">DAY STREAK</div>
          <div className="mission-side-sub">You're building momentum</div>
        </div>
      </div>

      <div className="dash-stat-grid">
        <div className="dash-stat-v2">
          <div className="dash-stat-icon violet">{StatIcon.briefcase}</div>
          <div className="dash-stat-num">{active}</div>
          <div className="dash-stat-label">Applications</div>
          <div className="dash-stat-delta up">↗ 12% this week</div>
        </div>
        <div className="dash-stat-v2">
          <div className="dash-stat-icon teal">{StatIcon.chat}</div>
          <div className="dash-stat-num">{interviews}</div>
          <div className="dash-stat-label">Interviews</div>
          <div className="dash-stat-delta up">↗ 2 this week</div>
        </div>
        <div className="dash-stat-v2">
          <div className="dash-stat-icon lime">{StatIcon.check}</div>
          <div className="dash-stat-num">{offers}</div>
          <div className="dash-stat-label">Offers</div>
          <div className="dash-stat-delta up">↗ 1 this week</div>
        </div>
        <div className="dash-stat-v2">
          <div className="dash-stat-icon orange">{StatIcon.bookmark}</div>
          <div className="dash-stat-num">{savedCount}</div>
          <div className="dash-stat-label">Saved</div>
          <div className="dash-stat-delta orange">↗ 4 this week</div>
        </div>
      </div>

      <div className="dash-strength-card">
        <div className="dash-strength-left">
          <h3>Profile Strength</h3>
          <p>Complete your profile to stand out more.</p>
          <button className="dash-improve-btn" onClick={onGoProfile}>Improve Profile →</button>
        </div>
        <ProgressRing pct={strength} />
      </div>
      <div className="dash-checklist">
        {checklist.map((c) => (
          <div key={c.label} className={`dash-check-item ${c.done ? 'done' : ''}`}>
            <span className="dash-check-mark">{c.done ? '✓' : '○'}</span> {c.label}
          </div>
        ))}
      </div>

      <div className="section" style={{ paddingTop: 22 }}>
        <div className="section-head-row">
          <div className="section-head"><h2>Activity overview</h2></div>
          <div className="activity-tabs">
            <button className="activity-tab active">7D</button>
            <button className="activity-tab">30D</button>
            <button className="activity-tab">90D</button>
          </div>
        </div>
      </div>
      <div className="activity-card">
        <div className="activity-legend"><span className="activity-dot" /> Applications</div>
        <div className="activity-chart-row">
          <ActivityChart data={ACTIVITY_TREND} days={ACTIVITY_DAYS} />
          <div className="activity-side">
            <div className="activity-side-num">{activityPeak}</div>
            <div className="activity-side-label">Applications</div>
            <div className="activity-side-delta up">↗ 12% vs last 7 days</div>
            <div className="activity-side-num" style={{ marginTop: 16 }}>156</div>
            <div className="activity-side-label">Profile Views</div>
            <div className="activity-side-delta violet">↗ 8% vs last 7 days</div>
          </div>
        </div>
      </div>

      <div className="section" style={{ paddingTop: 22 }}>
        <div className="section-head-row">
          <div className="section-head"><h2>Recommended for you</h2></div>
          <button className="result-count" onClick={onGoExplore} style={{ background: 'none', border: 'none', color: 'var(--lime-dim)', fontWeight: 700, cursor: 'pointer' }}>
            See all
          </button>
        </div>
      </div>

      {recommended.length === 0 ? (
        <div className="state-msg" style={{ margin: '0 20px' }}>No opportunities loaded yet — check the backend connection on Explore.</div>
      ) : (
        <div className="dash-carousel">
          {recommended.map((job) => (
            <div key={job.id} className="dash-carousel-item mini">
              <MiniJobCard job={job} isSaved={!!savedJobs[job.id]} onToggleSave={onToggleSave} onOpen={onOpen} />
            </div>
          ))}
        </div>
      )}

      <div className="bottom-pad" /><div className="bottom-pad" />
      <BottomNav active="dashboard" onNavigate={onNavigate} />
    </div>
  )
}
const APP_TABS = ['All', 'Active', 'Interview', 'Offer', 'Archived']
const APP_STATUSES = ['Applied', 'Under Review', 'Interview', 'Offer', 'Rejected', 'Archived']

function statusColor(status) {
  switch (status) {
    case 'Interview': return { bg: 'rgba(63,224,190,0.16)', fg: 'var(--teal)' }
    case 'Offer': return { bg: 'rgba(223,242,92,0.18)', fg: 'var(--lime-dim)' }
    case 'Rejected': return { bg: 'rgba(255,145,89,0.16)', fg: 'var(--orange)' }
    case 'Archived': return { bg: 'rgba(255,255,255,0.06)', fg: 'var(--muted-2)' }
    default: return { bg: 'rgba(255,145,89,0.16)', fg: 'var(--orange)' }
  }
}

function AddApplicationModal({ onClose, onAdd }) {
  const [company, setCompany] = useState('')
  const [title, setTitle] = useState('')
  const [location, setLocation] = useState('')
  const [status, setStatus] = useState('Applied')

  function submit() {
    if (!company.trim() || !title.trim()) return
    onAdd({
      company: company.trim(),
      title: title.trim(),
      location: location.trim() || 'Not specified',
      status,
      applied_date: new Date().toISOString().slice(0, 10),
      appliedDate: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    })
    onClose()
  }

  return (
    <div className="filters-backdrop" onClick={onClose}>
      <div className="filters-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="filters-head">
          <h3>Log an application</h3>
          <button className="filters-close" onClick={onClose}>✕</button>
        </div>

        <div className="form-field" style={{ marginTop: 16 }}>
          <label>Company</label>
          <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. CloudPlexo" />
        </div>
        <div className="form-field">
          <label>Role title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. SDR Trainee" />
        </div>
        <div className="form-field">
          <label>Location</label>
          <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Remote" />
        </div>
        <div className="form-field">
          <label>Status</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {APP_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="filters-footer">
          <button className="filters-apply-btn" onClick={submit}>Save application</button>
        </div>
      </div>
    </div>
  )
}

function ApplicationsPage({ applications, loadError, onAddApplication, onUpdateStatus, onDeleteApplication, onBack, onNavigate }) {
  const [activeTab, setActiveTab] = useState('All')
  const [showAddModal, setShowAddModal] = useState(false)

  const total = applications.length
  const active = applications.filter((a) => a.status !== 'Archived').length
  const interviews = applications.filter((a) => a.status === 'Interview').length
  const offers = applications.filter((a) => a.status === 'Offer').length

  const filtered = applications.filter((a) => {
    if (activeTab === 'All') return true
    if (activeTab === 'Active') return a.status !== 'Archived' && a.status !== 'Offer'
    return a.status === activeTab
  })

  function updateStatus(id, newStatus) {
    onUpdateStatus(id, newStatus)
  }

  function removeApp(id) {
    onDeleteApplication(id)
  }

  return (
    <div className="app">
      <div className="subpage-header">
        <button className="back-btn" onClick={onBack}>←</button>
        <div className="subpage-title">My Applications</div>
      </div>

      <div className="momentum-wrap">
        <div className="momentum-card">
          <div className="momentum-top">
            <div>
              <div className="momentum-num">{total}</div>
              <div className="momentum-label">Applications logged</div>
            </div>
          </div>
          <div className="stat-row">
            <div className="stat-pill"><b>{active}</b><span>ACTIVE</span></div>
            <div className="stat-pill"><b>{interviews}</b><span>INTERVIEWS</span></div>
            <div className="stat-pill"><b>{offers}</b><span>OFFERS</span></div>
          </div>
        </div>
      </div>

      <button className="add-app-fab" onClick={() => setShowAddModal(true)}>+ Log new application</button>

      <div className="app-tabs-wrap">
        <div className="app-tabs">
          {APP_TABS.map((t) => (
            <div key={t} className={`app-tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>{t}</div>
          ))}
        </div>
      </div>

      <div className="section">
        {loadError ? (
          <div className="state-msg error">
            Couldn't load your applications — check that the backend at {API_BASE} is running.
          </div>
        ) : filtered.length === 0 ? (
          <div className="saved-empty">
            <div className="saved-empty-icon">💼</div>
            <h3>Nothing here yet</h3>
            <p>Log an application above to start tracking it.</p>
          </div>
        ) : (
          filtered.map((a) => {
            const { bg, fg } = statusColor(a.status)
            return (
              <div key={a.id} className="app-card">
                <div className="app-top">
                  <div className="app-logo" style={{ background: bg, color: fg }}>{a.company.charAt(0).toUpperCase()}</div>
                  <div className="app-info">
                    <div className="app-title">{a.title}</div>
                    <div className="app-meta">{a.company} · {a.location}</div>
                  </div>
                  <div className="status-badge" style={{ background: bg, color: fg }}>{a.status}</div>
                </div>
                <div className="app-footer">
                  <span>Applied {a.appliedDate}</span>
                </div>
                <div className="app-actions">
                  <select className="app-status-select" value={a.status} onChange={(e) => updateStatus(a.id, e.target.value)}>
                    {APP_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <div className="app-del-btn" onClick={() => removeApp(a.id)}>✕</div>
                </div>
              </div>
            )
          })
        )}
      </div>

      <div className="bottom-pad" />
      <BottomNav active="applications" onNavigate={onNavigate} />

      {showAddModal && (
        <AddApplicationModal
          onClose={() => setShowAddModal(false)}
          onAdd={(app) => onAddApplication(app)}
        />
      )}
    </div>
  )
}

function ProfilePage({ savedCount, applicationsCount, apiFetch, authUser, onLogout, onBack, onNavigate }) {
  const [about, setAbout] = useState('')
  const [savedAbout, setSavedAbout] = useState('') // last value confirmed by the server, for revert-on-failure
  const [editingAbout, setEditingAbout] = useState(false)
  const [skills, setSkills] = useState([])
  const [addingSkill, setAddingSkill] = useState(false)
  const [newSkill, setNewSkill] = useState('')
  const [profileLoaded, setProfileLoaded] = useState(false)
  const [profileLoadError, setProfileLoadError] = useState(false)
  const [resumeName, setResumeName] = useState(null)
  const [resumeUploadedAt, setResumeUploadedAt] = useState(null)
  const [resumeUploading, setResumeUploading] = useState(false)
  const [resumeError, setResumeError] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    apiFetch('/profile')
      .then((r) => r.json())
      .then((data) => {
        setAbout(data.about || '')
        setSavedAbout(data.about || '')
        setSkills(data.skills || [])
        setResumeName(data.resume_original_name || null)
        setResumeUploadedAt(data.resume_uploaded_at || null)
        setProfileLoaded(true)
      })
      .catch(() => {
        setProfileLoaded(true)
        setProfileLoadError(true)
      })
  }, [])

  function pickResumeFile() {
    setResumeError(null)
    fileInputRef.current?.click()
  }

  function handleResumeFileChange(e) {
    const file = e.target.files?.[0]
    e.target.value = '' // allow re-selecting the same file later
    if (!file) return

    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!['.pdf', '.doc', '.docx'].includes(ext)) {
      setResumeError('Only PDF, DOC, or DOCX files are supported.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setResumeError('File is too large — 5MB limit.')
      return
    }

    setResumeUploading(true)
    setResumeError(null)
    const formData = new FormData()
    formData.append('file', file)

    apiFetch('/profile/resume', { method: 'POST', body: formData })
      .then((r) => {
        if (!r.ok) return r.json().then((d) => Promise.reject(d.detail || 'Upload failed'))
        return r.json()
      })
      .then((data) => {
        setResumeName(data.resume_original_name)
        setResumeUploadedAt(data.resume_uploaded_at)
      })
      .catch((err) => setResumeError(typeof err === 'string' ? err : 'Upload failed — try again.'))
      .finally(() => setResumeUploading(false))
  }

  function deleteResume() {
    setResumeError(null)
    const prevName = resumeName
    const prevDate = resumeUploadedAt
    setResumeName(null)
    setResumeUploadedAt(null)
    apiFetch('/profile/resume', { method: 'DELETE' }).catch(() => {
      setResumeName(prevName)
      setResumeUploadedAt(prevDate)
      setResumeError('Could not remove resume — try again.')
    })
  }

  function formatResumeDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr.replace(' ', 'T'))
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  function saveProfile(patch) {
    apiFetch('/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }).catch(() => {
      // revert on failure
      if ('about' in patch) setAbout(savedAbout)
    })
  }

  function finishEditingAbout() {
    setEditingAbout(false)
    setSavedAbout(about)
    saveProfile({ about })
  }

  function addSkill() {
    const s = newSkill.trim()
    if (s && !skills.includes(s)) {
      const next = [...skills, s]
      setSkills(next)
      saveProfile({ skills: next })
    }
    setNewSkill('')
    setAddingSkill(false)
  }

  function removeSkill(skill) {
    const next = skills.filter((s) => s !== skill)
    setSkills(next)
    saveProfile({ skills: next })
  }

  // Rough, transparent "profile strength" — just a count of filled sections, not a real scoring model.
  const filledSections = [about.trim().length > 20, skills.length > 0, true, true].filter(Boolean).length
  const strength = Math.round((filledSections / 4) * 100)

  return (
    <div className="app">
      <div className="subpage-header">
        <button className="back-btn" onClick={onBack}>←</button>
        <div className="subpage-title">My Profile</div>
      </div>

      <div className="section" style={{ paddingTop: 0 }}>
        <div className="section-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="resume-date">Signed in as {authUser?.email}</div>
          <button className="sc-edit" onClick={onLogout}>Log out</button>
        </div>
      </div>

      <div className="hero-card">
        <div className="hero-top">
          <div className="avatar-ring"><div className="avatar-inner">OA</div></div>
          <div>
            <div className="hero-name">Oyetunde Abbas</div>
            <div className="hero-headline">Computer Science Student · Final Year, KWASU</div>
            <div className="hero-score">{strength}% profile strength</div>
          </div>
        </div>
        <div className="quick-facts">
          <div className="qf-tag">🎓 KWASU '26</div>
          <div className="qf-tag">📍 Kwara State, Nigeria</div>
          <div className="qf-tag">💻 Remote / Hybrid</div>
        </div>
      </div>

      <div className="dash-stats-row" style={{ padding: '18px 20px 0' }}>
        <div className="dash-stat">
          <div className="dash-stat-num">{applicationsCount}</div>
          <div className="dash-stat-label">Applications</div>
        </div>
        <div className="dash-stat">
          <div className="dash-stat-num">{savedCount}</div>
          <div className="dash-stat-label">Saved</div>
        </div>
      </div>

      <div className="section" style={{ marginTop: 6 }}>
        <div className="section-card">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx"
            style={{ display: 'none' }}
            onChange={handleResumeFileChange}
          />
          <div className="resume-row">
            <div className="resume-icon">📄</div>
            <div className="resume-info">
              <div className="resume-name">
                {resumeUploading ? 'Uploading…' : resumeName || 'No resume uploaded'}
              </div>
              <div className="resume-date">
                {resumeUploading
                  ? ''
                  : resumeName
                  ? `Uploaded ${formatResumeDate(resumeUploadedAt)}`
                  : 'PDF, DOC, or DOCX · up to 5MB'}
              </div>
            </div>
            {!resumeUploading && (
              resumeName ? (
                <div style={{ display: 'flex', gap: 6 }}>
                  <a
                    className="sc-edit"
                    href={`${API_BASE}/profile/resume`}
                    style={{ textDecoration: 'none' }}
                  >
                    View
                  </a>
                  <button className="sc-edit" onClick={pickResumeFile}>Replace</button>
                  <button className="sc-edit" onClick={deleteResume}>Remove</button>
                </div>
              ) : (
                <button className="sc-edit" onClick={pickResumeFile}>Upload</button>
              )
            )}
          </div>
          {resumeError && (
            <div className="resume-date" style={{ color: 'var(--orange)', marginTop: 8 }}>{resumeError}</div>
          )}
        </div>
      </div>

      {profileLoadError ? (
        <div className="section">
          <div className="state-msg error">
            Couldn't load your profile — check that the backend at {API_BASE} is running. About me and Skills won't be editable until it's reachable.
          </div>
        </div>
      ) : (
        <>
      <div className="section">
        <div className="section-card">
          <div className="sc-head">
            <h3>About me</h3>
            <button className="sc-edit" onClick={() => (editingAbout ? finishEditingAbout() : setEditingAbout(true))}>{editingAbout ? 'Done' : 'Edit'}</button>
          </div>
          <div className="about-text">
            {editingAbout ? (
              <textarea value={about} onChange={(e) => setAbout(e.target.value)} />
            ) : (
              about
            )}
          </div>
        </div>
      </div>

      <div className="section">
        <div className="section-card">
          <div className="sc-head">
            <h3>Skills</h3>
            <button className="sc-add" onClick={() => setAddingSkill((v) => !v)}>+ Add</button>
          </div>
          <div className="skill-chips">
            {skills.map((s) => (
              <div key={s} className="skill-chip">
                {s} <span className="rm" onClick={() => removeSkill(s)}>✕</span>
              </div>
            ))}
          </div>
          {addingSkill && (
            <div className="skill-add-row">
              <input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                placeholder="e.g. Docker"
                onKeyDown={(e) => e.key === 'Enter' && addSkill()}
              />
              <button onClick={addSkill}>Add</button>
            </div>
          )}
        </div>
      </div>
      </>
      )}

      <div className="section">
        <div className="section-card">
          <div className="sc-head"><h3>Experience</h3></div>
          <div className="exp-item">
            <div className="exp-icon" style={{ background: 'rgba(155,107,255,0.16)', color: 'var(--violet)' }}>💼</div>
            <div>
              <div className="exp-role">SIWES Trainee, Cloud & Security</div>
              <div className="exp-org">United Bank for Africa</div>
              <div className="exp-desc">Hands-on with AWS IAM, VPC, and EC2 during industrial placement.</div>
            </div>
          </div>
          <div className="exp-item">
            <div className="exp-icon" style={{ background: 'rgba(63,224,190,0.16)', color: 'var(--teal)' }}>🎓</div>
            <div>
              <div className="exp-role">AI &amp; ML Scholar</div>
              <div className="exp-org">Udacity × AWS Program · Ongoing</div>
              <div className="exp-desc">Built and deployed a DenseNet121 model for diabetic retinopathy detection, 96.19% accuracy.</div>
            </div>
          </div>
        </div>
      </div>

      <div className="bottom-pad" />
      <BottomNav active="profile" onNavigate={onNavigate} />
    </div>
  )
}

function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState('login') // login | signup
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  function submit(e) {
    e.preventDefault()
    setError(null)

    if (!email.trim() || !password) {
      setError('Enter your email and password.')
      return
    }
    if (mode === 'signup' && password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setSubmitting(true)
    fetch(`${API_BASE}/auth/${mode}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    })
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Something went wrong')
        return data
      })
      .then((data) => onAuthSuccess(data.token, data.user))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="app">
      <div className="hero" style={{ paddingBottom: 8 }}>
        <h1>Welcome to <b>Undergrad</b></h1>
        <p>Track real opportunities, save your favorites, and manage your applications in one place.</p>
      </div>

      <div className="section" style={{ paddingTop: 8 }}>
        <div className="section-card">
          <div className="sc-head" style={{ marginBottom: 12 }}>
            <h3>{mode === 'login' ? 'Log in' : 'Create your account'}</h3>
          </div>

          <form onSubmit={submit}>
            <div className="form-field" style={{ margin: '0 0 14px' }}>
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>
            <div className="form-field" style={{ margin: '0 0 14px' }}>
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === 'signup' ? 'At least 8 characters' : 'Your password'}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <div className="state-msg error" style={{ padding: '0 0 14px', textAlign: 'left' }}>
                {error}
              </div>
            )}

            <button type="submit" className="filters-apply-btn" disabled={submitting}>
              {submitting ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Sign up'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 16, fontSize: 12.5, color: 'var(--muted)' }}>
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <span
              style={{ color: 'var(--lime)', fontWeight: 700, cursor: 'pointer' }}
              onClick={() => {
                setMode(mode === 'login' ? 'signup' : 'login')
                setError(null)
              }}
            >
              {mode === 'login' ? 'Sign up' : 'Log in'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('undergrad_token') || null)
  const [authUser, setAuthUser] = useState(null)
  const [authChecking, setAuthChecking] = useState(true)

  function apiFetch(path, options = {}) {
    const headers = { ...(options.headers || {}) }
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`
    return fetch(`${API_BASE}${path}`, { ...options, headers }).then((res) => {
      if (res.status === 401) logout()
      return res
    })
  }

  function persistAuth(token, user) {
    localStorage.setItem('undergrad_token', token)
    setAuthToken(token)
    setAuthUser(user)
  }

  function logout() {
    localStorage.removeItem('undergrad_token')
    setAuthToken(null)
    setAuthUser(null)
    // clear anything that belonged to the previous session so a different
    // user logging in on the same device never briefly sees stale data
    setSavedJobs({})
    setApplications([])
    setView('explore')
  }

  useEffect(() => {
    if (!authToken) {
      setAuthChecking(false)
      return
    }
    fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${authToken}` } })
      .then((res) => {
        if (!res.ok) throw new Error('invalid session')
        return res.json()
      })
      .then((user) => {
        setAuthUser(user)
        setAuthChecking(false)
      })
      .catch(() => {
        localStorage.removeItem('undergrad_token')
        setAuthToken(null)
        setAuthUser(null)
        setAuthChecking(false)
      })
  }, [])

  const [view, setView] = useState('explore') // explore | detail | saved | applications | profile | dashboard
  const [selectedJob, setSelectedJob] = useState(null)
  const [savedJobs, setSavedJobs] = useState({}) // keyed by listing id, persisted via /saved API
  const [applications, setApplications] = useState([]) // persisted via /applications API
  const [savedLoadError, setSavedLoadError] = useState(false)
  const [applicationsLoadError, setApplicationsLoadError] = useState(false)

  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [workStyleIdx, setWorkStyleIdx] = useState(0)
  const [activeType, setActiveType] = useState('')
  const [activeLocation, setActiveLocation] = useState('')
  const [locationMenuOpen, setLocationMenuOpen] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)

  const [locations, setLocations] = useState([])

  const [jobs, setJobs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)

  const requestId = useRef(0)

  function formatAppliedDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  function toggleSave(job) {
    const isSaved = !!savedJobs[job.id]
    // optimistic update
    setSavedJobs((prev) => {
      const next = { ...prev }
      if (isSaved) delete next[job.id]
      else next[job.id] = job
      return next
    })
    const req = isSaved
      ? apiFetch(`/saved/${job.id}`, { method: 'DELETE' })
      : apiFetch('/saved', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ listing_id: job.id }),
        })
    req.catch(() => {
      // revert on failure
      setSavedJobs((prev) => {
        const next = { ...prev }
        if (isSaved) next[job.id] = job
        else delete next[job.id]
        return next
      })
    })
  }

  function addApplication(app) {
    // optimistic temp entry, replaced once the server assigns a real id
    const tempId = `temp-${Date.now()}`
    setApplications((prev) => [{ ...app, id: tempId }, ...prev])
    apiFetch('/applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: app.title,
        company: app.company,
        location: app.location,
        status: app.status,
        applied_date: app.applied_date,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        setApplications((prev) => prev.map((a) => (a.id === tempId ? { ...a, id: data.id } : a)))
      })
      .catch(() => {
        setApplications((prev) => prev.filter((a) => a.id !== tempId))
      })
  }

  function updateApplicationStatus(id, newStatus) {
    setApplications((prev) => prev.map((a) => (a.id === id ? { ...a, status: newStatus } : a)))
    apiFetch(`/applications/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    }).catch(() => {})
  }

  function deleteApplication(id) {
    const prevApps = applications
    setApplications((prev) => prev.filter((a) => a.id !== id))
    apiFetch(`/applications/${id}`, { method: 'DELETE' }).catch(() => {
      setApplications(prevApps)
    })
  }

  function openJob(job) {
    setSelectedJob(job)
    setView('detail')
  }

  useEffect(() => {
    if (!authToken) return
    apiFetch('/saved')
      .then((res) => res.json())
      .then((data) => {
        const map = {}
        for (const job of data.saved || []) map[job.id] = job
        setSavedJobs(map)
      })
      .catch(() => setSavedLoadError(true))

    apiFetch('/applications')
      .then((res) => res.json())
      .then((data) => {
        const mapped = (data.applications || []).map((a) => ({
          ...a,
          appliedDate: formatAppliedDate(a.applied_date || a.created_at),
        }))
        setApplications(mapped)
      })
      .catch(() => setApplicationsLoadError(true))
  }, [authToken])

  useEffect(() => {
    fetch(`${API_BASE}/jobs/locations`)
      .then((res) => res.json())
      .then((data) => setLocations(Array.isArray(data) ? data.slice(0, 25) : []))
      .catch(() => setLocations([]))
  }, [])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350)
    return () => clearTimeout(t)
  }, [search])

  const params = useMemo(() => {
    const p = new URLSearchParams()
    p.set('limit', String(PAGE_LIMIT))
    if (debouncedSearch) p.set('search', debouncedSearch)
    const remote = WORK_STYLE_CHIPS[workStyleIdx].remote
    if (remote !== null) p.set('remote', String(remote))
    if (activeType) p.set('job_type', activeType)
    if (activeLocation) p.set('location', activeLocation)
    return p
  }, [debouncedSearch, workStyleIdx, activeType, activeLocation])

  useEffect(() => {
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    setPage(1)

    const p = new URLSearchParams(params)
    p.set('page', '1')

    fetch(`${API_BASE}/jobs?${p.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Server returned ${res.status}`)
        return res.json()
      })
      .then((data) => {
        if (id !== requestId.current) return
        setJobs(data.jobs || [])
        setTotal(data.total || 0)
      })
      .catch((err) => {
        if (id !== requestId.current) return
        setError(err.message || 'Could not reach the backend')
        setJobs([])
        setTotal(0)
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false)
      })
  }, [params])

  function loadMore() {
    const nextPage = page + 1
    setLoadingMore(true)
    const p = new URLSearchParams(params)
    p.set('page', String(nextPage))

    fetch(`${API_BASE}/jobs?${p.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Server returned ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setJobs((prev) => [...prev, ...(data.jobs || [])])
        setPage(nextPage)
      })
      .catch((err) => setError(err.message || 'Could not load more'))
      .finally(() => setLoadingMore(false))
  }

  function resetFilters() {
    setWorkStyleIdx(0)
    setActiveType('')
    setActiveLocation('')
  }

  const hasMore = jobs.length < total

  if (authChecking) {
    return (
      <div className="app">
        <div className="state-msg">Loading…</div>
      </div>
    )
  }

  if (!authToken || !authUser) {
    return <AuthPage onAuthSuccess={(token, user) => persistAuth(token, user)} />
  }

  if (view === 'detail' && selectedJob) {
    return (
      <JobDetailPage
        job={selectedJob}
        isSaved={!!savedJobs[selectedJob.id]}
        onToggleSave={toggleSave}
        onBack={() => setView('explore')}
        onNavigate={setView}
      />
    )
  }

  if (view === 'saved') {
    return (
      <SavedPage
        savedJobs={savedJobs}
        loadError={savedLoadError}
        onToggleSave={toggleSave}
        onOpen={openJob}
        onBack={() => setView('explore')}
        onNavigate={setView}
      />
    )
  }

  if (view === 'dashboard') {
    return (
      <DashboardPage
        userName="Abbas"
        jobs={jobs}
        savedJobs={savedJobs}
        applications={applications}
        onToggleSave={toggleSave}
        onOpen={openJob}
        onGoExplore={() => setView('explore')}
        onGoApplications={() => setView('applications')}
        onGoSaved={() => setView('saved')}
        onGoProfile={() => setView('profile')}
        onNavigate={setView}
      />
    )
  }

  if (view === 'applications') {
    return (
      <ApplicationsPage
        applications={applications}
        loadError={applicationsLoadError}
        onAddApplication={addApplication}
        onUpdateStatus={updateApplicationStatus}
        onDeleteApplication={deleteApplication}
        onBack={() => setView('explore')}
        onNavigate={setView}
      />
    )
  }

  if (view === 'profile') {
    return (
      <ProfilePage
        savedCount={Object.keys(savedJobs).length}
        applicationsCount={applications.length}
        apiFetch={apiFetch}
        authUser={authUser}
        onLogout={logout}
        onBack={() => setView('explore')}
        onNavigate={setView}
      />
    )
  }

  return (
    <div className="app">
      <div className="header">
        <div className="header-left">
          <img src={LOGO_DATA_URI} className="logo-mark" alt="Undergrad U" />
          <span className="wordmark">under<b>grad</b></span>
        </div>
        <div className="bell">🔔</div>
      </div>

      <div className="hero">
        <h1>Find your <b>next step.</b></h1>
        <p>Internships, SIWES, grad programs, and entry-level roles — pulled live from your database.</p>
      </div>

      <div className="search-row">
        <div className="search-bar">
          <span className="ic">⌕</span>
          <input
            type="text"
            placeholder="Search roles, skills, or companies"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button className="filter-btn" onClick={() => setFiltersOpen(true)} title="Filters">
          <svg viewBox="0 0 24 24"><line x1="4" y1="7" x2="20" y2="7"/><circle cx="9" cy="7" r="2.3" fill="currentColor" stroke="none"/><line x1="4" y1="17" x2="20" y2="17"/><circle cx="16" cy="17" r="2.3" fill="currentColor" stroke="none"/></svg>
        </button>
        <div style={{ position: 'relative' }}>
          <button className="loc-pill" onClick={() => setLocationMenuOpen((v) => !v)}>
            📍 {activeLocation || 'Any location'} <span className="loc-chevron">⌄</span>
          </button>
          {locationMenuOpen && (
            <div className="loc-menu">
              <button className={`loc-menu-item ${activeLocation === '' ? 'active' : ''}`} onClick={() => { setActiveLocation(''); setLocationMenuOpen(false) }}>
                Any location
              </button>
              {locations.map((loc) => (
                <button key={loc} className={`loc-menu-item ${activeLocation === loc ? 'active' : ''}`} onClick={() => { setActiveLocation(loc); setLocationMenuOpen(false) }}>
                  {loc}
                </button>
              ))}
              {locations.length === 0 && <div className="loc-menu-empty">No locations loaded yet</div>}
            </div>
          )}
        </div>
      </div>

      <div className="pop-wrap">
        <div className="pop-head">
          <div className="pop-label">Work style</div>
        </div>
        <div className="chips">
          {WORK_STYLE_CHIPS.map((c, i) => (
            <button key={c.label} className={`chip ${i === workStyleIdx ? 'active' : ''}`} onClick={() => setWorkStyleIdx(i)}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="section">
        <div className="section-head-row">
          <div className="section-head"><h2>Opportunities for you</h2></div>
          {!loading && !error && <div className="result-count">{total} found</div>}
        </div>

        {loading && <div className="state-msg">Loading opportunities…</div>}

        {error && (
          <div className="state-msg error">
            Couldn't reach the backend at {API_BASE}. Is it running? ({error})
          </div>
        )}

        {!loading && !error && jobs.length === 0 && (
          <div className="state-msg">No opportunities match these filters yet.</div>
        )}

        {!loading && !error && jobs.length > 0 && (
          <div className="job-list">
            {jobs.map((job, i) => (
              <JobCard
                key={job.id}
                job={job}
                featured={i === 0 && page === 1}
                isSaved={!!savedJobs[job.id]}
                onToggleSave={toggleSave}
                onOpen={openJob}
              />
            ))}
            {hasMore && (
              <button className="load-more" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading…' : `Load more (${jobs.length} of ${total})`}
              </button>
            )}
          </div>
        )}

        <div className="bottom-pad" />
      </div>

      <BottomNav active="explore" onNavigate={setView} />

      {filtersOpen && (
        <FiltersModal
          workStyleIdx={workStyleIdx} setWorkStyleIdx={setWorkStyleIdx}
          activeType={activeType} setActiveType={setActiveType}
          activeLocation={activeLocation} setActiveLocation={setActiveLocation}
          locations={locations}
          onClose={() => setFiltersOpen(false)}
          onReset={resetFilters}
          resultCount={total}
        />
      )}
    </div>
  )
}
