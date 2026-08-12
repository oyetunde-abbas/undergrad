import React from 'react';
import { createRoot } from 'react-dom/client';
import { Bell, Bookmark, BriefcaseBusiness, ChevronRight, Filter, MapPin, Search, Sparkles } from 'lucide-react';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const chipOptions = [
  { label: 'All', value: '' },
  { label: 'Internships', value: 'Internship' },
  { label: 'Graduate', value: 'Graduate' },
  { label: 'Remote', value: 'remote' },
];

function initials(company = '') {
  return company.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'U';
}

function Explore() {
  const [jobs, setJobs] = React.useState([]);
  const [search, setSearch] = React.useState('');
  const [location, setLocation] = React.useState('');
  const [activeChip, setActiveChip] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');
  const [saved, setSaved] = React.useState(() => new Set());
  const [filterOpen, setFilterOpen] = React.useState(false);

  const loadJobs = React.useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ page: '1', limit: '20', sort: 'newest' });
      if (search.trim()) params.set('search', search.trim());
      if (location.trim()) params.set('location', location.trim());
      if (activeChip === 'remote') params.set('remote', 'true');
      if (activeChip && activeChip !== 'remote') params.set('job_type', activeChip);

      const response = await fetch(`${API_BASE}/jobs?${params}`);
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setJobs(Array.isArray(data.jobs) ? data.jobs : []);
    } catch (err) {
      setError('Could not load opportunities. Make sure the Undergrad API is running.');
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, [search, location, activeChip]);

  React.useEffect(() => {
    const timer = setTimeout(loadJobs, 300);
    return () => clearTimeout(timer);
  }, [loadJobs]);

  const toggleSave = (id) => {
    setSaved((current) => {
      const next = new Set(current);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="app-shell">
      <main className="phone">
        <div className="ambient ambient-orange" />
        <div className="ambient ambient-purple" />
        <div className="ambient ambient-teal" />

        <div className="scroll">
          <header className="header">
            <div className="brand"><div className="brand-mark">U</div><span>under<b>grad</b></span></div>
            <button className="icon-button notification" aria-label="Notifications"><Bell size={17} /></button>
          </header>

          <section className="intro">
            <div className="eyebrow"><span /> EXPLORE</div>
            <h1>Find your next<br /><span>step.</span></h1>
            <p>Discover opportunities matched to where you are and where you want to go.</p>
          </section>

          <section className="search-wrap">
            <label className="search-bar">
              <Search size={16} />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search roles, skills or companies" />
            </label>
            <button className="loc-pill" onClick={() => setFilterOpen(true)}><MapPin size={14} />{location || 'Lagos'}</button>
          </section>

          <section className="chips-wrap">
            <div className="chips-label">QUICK FILTERS</div>
            <div className="chips">
              {chipOptions.map((chip) => (
                <button key={chip.label} className={`chip ${activeChip === chip.value ? 'active' : ''}`} onClick={() => setActiveChip(chip.value)}>{chip.label}</button>
              ))}
              <button className="chip filter-chip" onClick={() => setFilterOpen(true)}><Filter size={13} /> More filters</button>
            </div>
          </section>

          <section className="section">
            <div className="section-head-row">
              <div><div className="recommended-pill"><span className="dot" /> For you</div><h2>Recommended opportunities</h2></div>
              <button className="see-all" onClick={() => { setSearch(''); setLocation(''); setActiveChip(''); }}>Reset</button>
            </div>

            {loading && <div className="state">Finding opportunities<span className="pulse">...</span></div>}
            {!loading && error && <div className="state error">{error}</div>}
            {!loading && !error && jobs.length === 0 && <div className="state">No opportunities match those filters.</div>}

            <div className="job-list">
              {jobs.map((job) => {
                const isSaved = saved.has(job.id);
                return (
                  <article className="job-card" key={job.id}>
                    <div className="job-top">
                      <div className="job-logo">{initials(job.company)}</div>
                      <div className="job-info">
                        <h3>{job.title || 'Untitled opportunity'}</h3>
                        <p>{job.company || 'Company'} <span>•</span> {job.location || (job.remote ? 'Remote' : 'Location not listed')}</p>
                      </div>
                      <button className={`save-btn ${isSaved ? 'saved' : ''}`} onClick={() => toggleSave(job.id)} aria-label="Save opportunity"><Bookmark size={15} fill={isSaved ? 'currentColor' : 'none'} /></button>
                    </div>
                    <div className="job-tags">
                      {job.type && <span className="tag lime">{job.type}</span>}
                      {job.work_style && <span className="tag violet">{job.work_style}</span>}
                      {job.experience_level && <span className="tag teal">{job.experience_level}</span>}
                    </div>
                    <div className="why-line"><span className="why-icon"><Sparkles size={11} /></span><span><b>Why it stands out:</b> {job.skills ? `Skills include ${job.skills.split(',').slice(0, 2).join(' and ')}.` : 'A relevant opportunity from the Undergrad feed.'}</span></div>
                    <a className="job-cta" href={job.apply_url || '#'} target="_blank" rel="noreferrer">View opportunity <ChevronRight size={15} /></a>
                  </article>
                );
              })}
            </div>
          </section>
          <div className="bottom-pad" />
        </div>

        <nav className="navbar">
          <div className="nav-item active"><BriefcaseBusiness size={18} /><span>Explore</span></div>
          <div className="nav-item"><Bookmark size={18} /><span>Saved</span></div>
          <div className="nav-item"><Sparkles size={18} /><span>For you</span></div>
          <div className="nav-item"><div className="profile-dot">A</div><span>Profile</span></div>
        </nav>

        {filterOpen && <div className="sheet-overlay open" onClick={() => setFilterOpen(false)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-handle" />
            <div className="sheet-top"><h3>Filter opportunities</h3><button className="close-x" onClick={() => setFilterOpen(false)}>×</button></div>
            <label className="sheet-field"><span>Location</span><input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Lagos, Abuja, Remote..." /></label>
            <div className="filter-group"><div className="filter-group-title">Job type</div><div className="filter-chips">{['Internship', 'Graduate', 'Full-time'].map((type) => <button key={type} className={`sheet-chip ${activeChip === type ? 'selected' : ''}`} onClick={() => setActiveChip(type)}>{type}</button>)}</div></div>
            <button className="sheet-cta" onClick={() => setFilterOpen(false)}>Show opportunities</button>
          </div>
        </div>}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<Explore />);
