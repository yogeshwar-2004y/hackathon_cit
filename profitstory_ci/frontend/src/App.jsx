import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Play, Diamond, Circle, Triangle, Settings, LineChart, FileText, Bell, Users, Search, Target, Database } from 'lucide-react';
import './index.css';

// Default: good-our-product / bad-competitor (real input for vulnerability signals)
const DEFAULT_PRODUCT_ASIN = 'B0863TXGM3';   // Sony WH-1000XM4 (premium, good reviews)
const DEFAULT_COMPETITOR_ASINS = 'B0F7LY85KB';  // boAt Rockerz 421 (budget, often worse reviews)

function DonutRing({ score, colorClass }) {
  const r = 23;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  
  return (
    <div className="donut">
      <svg viewBox="0 0 50 50">
        <circle className="donut-bg" cx="25" cy="25" r={r} />
        <circle 
          className={`donut-fill ${colorClass}`} 
          cx="25" cy="25" r={r} 
          strokeDasharray={`${filled} ${circ}`} 
          strokeDashoffset={0}
        />
      </svg>
      <div className={`donut-text ${colorClass}`}>{Math.round(score)}</div>
    </div>
  );
}

function scoreToColorClass(score) {
  if (score > 70) return 'red';
  if (score > 40) return 'yellow';
  if (score > 20) return 'blue';
  return 'green';
}

function App() {
  const [scanning, setScanning] = useState(false);
  const [activeTab, setActiveTab] = useState('INTELLIGENCE');
  const [results, setResults] = useState(null);
  const [logs, setLogs] = useState([]);
  const [productAsin, setProductAsin] = useState(DEFAULT_PRODUCT_ASIN);
  const [competitorAsins, setCompetitorAsins] = useState(DEFAULT_COMPETITOR_ASINS);
  const [backendLogs, setBackendLogs] = useState([]);
  const [backendLogsLoading, setBackendLogsLoading] = useState(false);
  const [embeddings, setEmbeddings] = useState({ count: 0, embeddings: [] });
  const [embeddingsLoading, setEmbeddingsLoading] = useState(false);
  const [embeddingsFilterAsin, setEmbeddingsFilterAsin] = useState('');

  const fetchEmbeddings = useCallback(async () => {
    setEmbeddingsLoading(true);
    try {
      const q = embeddingsFilterAsin ? `?asin=${encodeURIComponent(embeddingsFilterAsin)}` : '';
      const res = await fetch(`/api/embeddings${q}`);
      const data = await res.json();
      setEmbeddings({ count: data.count ?? 0, embeddings: data.embeddings ?? [] });
    } catch (e) {
      setEmbeddings({ count: 0, embeddings: [], error: String(e.message) });
    } finally {
      setEmbeddingsLoading(false);
    }
  }, [embeddingsFilterAsin]);

  const fetchBackendLogs = useCallback(async () => {
    setBackendLogsLoading(true);
    try {
      const res = await fetch('/api/logs?limit=100');
      const data = await res.json();
      setBackendLogs(data.lines || []);
    } catch (e) {
      setBackendLogs([{ msg: 'Failed to load logs', error: true }]);
    } finally {
      setBackendLogsLoading(false);
    }
  }, []);

  const fetchLatestResults = useCallback(async () => {
    try {
      const res = await fetch('/api/results/latest');
      const data = await res.json();
      if (data.status === 'success') setResults(data);
      else setResults(null);
    } catch (e) {
      console.error('Failed to fetch results:', e);
      setResults(null);
    }
  }, []);

  useEffect(() => {
    fetchLatestResults();
  }, [fetchLatestResults]);

  useEffect(() => {
    if (activeTab === 'INTELLIGENCE') fetchBackendLogs();
  }, [activeTab, fetchBackendLogs]);

  useEffect(() => {
    if (activeTab === 'EMBEDDINGS') fetchEmbeddings();
  }, [activeTab, fetchEmbeddings]);

  // Auto-refresh backend logs while a scan is running (every 8s to avoid flooding /logs)
  useEffect(() => {
    if (!scanning) return;
    const interval = setInterval(fetchBackendLogs, 8000);
    return () => clearInterval(interval);
  }, [scanning, fetchBackendLogs]);

  const handleScan = useCallback(async () => {
    if (scanning) return;
    setScanning(true);
    setLogs([]);
    try {
      const url = `/api/scan?product_asin=${encodeURIComponent(productAsin)}&competitor_asins=${encodeURIComponent(competitorAsins)}`;
      const res = await fetch(url, { method: 'POST' });
      const { job_id } = await res.json();
      const source = new EventSource(`/api/job/${job_id}/stream`);
      source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status === 'done' || data.status === 'error') {
          source.close();
          setScanning(false);
          if (data.status === 'done') fetchLatestResults();
          fetchBackendLogs();
          return;
        }
        setLogs((prev) => [...prev, data]);
      };
      source.onerror = () => {
        source.close();
        setScanning(false);
        fetchLatestResults();
        fetchBackendLogs();
      };
    } catch (e) {
      console.error('Scan failed:', e);
      setScanning(false);
    }
  }, [scanning, productAsin, competitorAsins, fetchLatestResults, fetchBackendLogs]);

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="brand-logo">PROFITSTORY.AI</div>
        
        <div className="nav-section">
          <div className={`nav-item ${activeTab === 'INTELLIGENCE' ? 'active' : ''}`} onClick={() => setActiveTab('INTELLIGENCE')}>
            <Circle size={14} /> INTELLIGENCE
          </div>
          <div className={`nav-item ${activeTab === 'COMPETITORS' ? 'active' : ''}`} onClick={() => setActiveTab('COMPETITORS')}>
            <Diamond size={14} /> COMPETITORS
          </div>
          <div className={`nav-item ${activeTab === 'PIVOT MEMOS' ? 'active' : ''}`} onClick={() => setActiveTab('PIVOT MEMOS')}>
            <Triangle size={14} /> PIVOT MEMOS
          </div>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Analytics</div>
          <div className={`nav-item ${activeTab === 'PROFIT SIM' ? 'active' : ''}`} onClick={() => setActiveTab('PROFIT SIM')}>
            <LineChart size={14} /> PROFIT SIM
          </div>
          <div className={`nav-item ${activeTab === 'REVIEWS' ? 'active' : ''}`} onClick={() => setActiveTab('REVIEWS')}>
            <Search size={14} /> REVIEWS
          </div>
          <div className={`nav-item ${activeTab === 'ALERTS' ? 'active' : ''}`} onClick={() => setActiveTab('ALERTS')}>
            <Bell size={14} /> ALERTS
          </div>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Data</div>
          <div className={`nav-item ${activeTab === 'EMBEDDINGS' ? 'active' : ''}`} onClick={() => setActiveTab('EMBEDDINGS')}>
            <Database size={14} /> EMBEDDINGS
          </div>
        </div>
        <div className="nav-section" style={{marginTop: 'auto'}}>
          <div className="nav-section-title">Settings</div>
          <div className={`nav-item ${activeTab === 'PRODUCTS' ? 'active' : ''}`} onClick={() => setActiveTab('PRODUCTS')}>
            <Target size={14} /> PRODUCTS
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">
        {activeTab === 'INTELLIGENCE' && (
          <>
            <div className="header">
          <div>
            <div className="header-subtitle">MONITORING PRODUCT</div>
            <h1 className="header-title">
              {results?.products?.[productAsin]?.name || 'Your Product'} <span className="header-pill">{productAsin}</span>
            </h1>
          </div>
          <button 
            className={`btn-scan ${scanning ? 'scanning' : ''}`} 
            onClick={handleScan}
          >
            <RefreshCw size={14} className={scanning ? 'animate-pulse' : ''} />
            {scanning ? 'Running Agent...' : 'Run Agent Scan'}
          </button>
        </div>

        {/* METRICS ROW — from backend results only */}
        <div className="metrics-row">
          <div className="metric-card">
            <div className="metric-title">YOUR PRICE</div>
            <div className="metric-value white">
              {results?.products?.[productAsin]?.price != null ? `₹${Number(results.products[productAsin].price).toLocaleString()}` : '—'}
            </div>
            <div className="metric-subtitle">{results?.products?.[productAsin] ? 'From last scan' : 'Run scan'}</div>
            <div className="metric-bar-container" style={{marginTop: '16px'}}>
              <div className="metric-bar" style={{width: '45%', background: '#10B981'}}></div>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-title">MARGIN AT RISK</div>
            <div className="metric-value red">
              {results?.profit_sims?.match?.net_profit != null ? `₹${Math.abs(results.profit_sims.match.net_profit).toLocaleString()}` : '—'}
            </div>
            <div className="metric-subtitle">If matched comp price</div>
            <div className="metric-bar-container" style={{background: '#3B1B1B', marginTop: '16px'}}>
              <div className="metric-bar" style={{width: '70%', background: '#EF4444'}}></div>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-title">PIVOT UPSIDE</div>
            <div className="metric-value green">
              {results?.profit_sims?.ads?.net_profit != null && results.profit_sims.ads.net_profit > 0
                ? `+₹${results.profit_sims.ads.net_profit.toLocaleString()}`
                : '—'}
            </div>
            <div className="metric-subtitle">Best strategy net gain</div>
            <div className="metric-bar-container" style={{background: '#133A2A', marginTop: '16px'}}>
              <div className="metric-bar" style={{width: '85%', background: '#10B981'}}></div>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-title">SIGNALS DETECTED</div>
            <div className="metric-value yellow">
              {results?.signals ? results.signals.reduce((n, s) => n + (s.signals?.length || 0), 0) : '—'}
            </div>
            <div className="metric-subtitle">
              {results?.signals?.length ? `${results.signals.length} competitor(s)` : 'Run scan'}
            </div>
            <div className="metric-bar-container" style={{background: '#3F2C15', marginTop: '16px'}}>
              <div className="metric-bar" style={{width: '60%', background: '#F59E0B'}}></div>
            </div>
          </div>
        </div>

        <div className="dashboard-grid">
          {/* LEFT COL */}
          <div className="dashboard-left">
            <div className="panel" style={{marginBottom: '24px'}}>
              <div className="panel-header">COMPETITOR VULNERABILITY</div>
              
              <div className="competitor-list">
                {results?.vuln_scores && Object.keys(results.vuln_scores).length > 0
                  ? Object.entries(results.vuln_scores).map(([asin, v]) => {
                      const product = results?.products?.[asin];
                      const name = product?.name || `Competitor ${asin}`;
                      return (
                        <div key={asin} className="competitor-item">
                          <div className="comp-info">
                            <h4>{name}</h4>
                            <span className="comp-desc">{asin}{product?.review_count != null ? ` · ${product.review_count} reviews` : ''}</span>
                          </div>
                          <div className="comp-stats">
                            {product?.price != null && <div className="comp-price-row">₹{Number(product.price).toLocaleString()}</div>}
                            <div className={`badge ${scoreToColorClass(v.score)}`}>
                              {Math.round(v.score)} · {v.label?.toUpperCase() || 'N/A'}
                            </div>
                          </div>
                          <DonutRing score={v.score} colorClass={scoreToColorClass(v.score)} />
                        </div>
                      );
                    })
                  : (
                    <div className="empty-state">
                      No competitor data yet. Run an agent scan to scrape and analyze competitors.
                    </div>
                  )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header" style={{margin: '0 0 16px 0', border: 'none'}}>SCORE FORMULA</div>
              <div className="formula-grid">
                <div className="formula-box">
                  <span className="formula-multiplier">×0.4</span>
                  <span className="formula-label">Neg Sentiment</span>
                </div>
                <div className="formula-box">
                  <span className="formula-multiplier">×0.3</span>
                  <span className="formula-label">Price Drop %</span>
                </div>
                <div className="formula-box">
                  <span className="formula-multiplier">×0.2</span>
                  <span className="formula-label">Review Spike</span>
                </div>
                <div className="formula-box">
                  <span className="formula-multiplier">×0.1</span>
                  <span className="formula-label">Rating Drop</span>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT COL */}
          <div className="dashboard-right">
            <div className="panel" style={{marginBottom: '24px'}}>
              <div className="panel-header">REVIEW SIGNALS</div>
              
              <div className="signals-list">
                {results?.signals?.length > 0
                  ? results.signals.flatMap((sig) =>
                      (sig.signals || []).map((s, i) => {
                        const type = typeof s.type === 'string' ? s.type : 'low';
                        const text = typeof s.text === 'string' ? s.text : (s.text?.text ?? JSON.stringify(s.text ?? s));
                        return (
                          <div key={`${sig.asin}-${i}`} className="signal-item">
                            <div className={`signal-dot ${type === 'critical' ? 'red' : type === 'medium' ? 'yellow' : 'green'}`}></div>
                            <div className="signal-text">{text}</div>
                          </div>
                        );
                      })
                    )
                  : (
                    <div className="empty-state">Run an agent scan to see detected signals from competitor reviews and pricing.</div>
                  )}
              </div>
            </div>

            {logs.length > 0 && (
              <div className="panel" style={{marginBottom: '24px'}}>
                <div className="panel-header">AGENT LOG (live)</div>
                <div className="agent-log" style={{ maxHeight: 200, overflow: 'auto', fontFamily: 'monospace', fontSize: 12 }}>
                  {logs.map((line, i) => {
                    const msg = line.msg != null && typeof line.msg !== 'object' ? String(line.msg) : (line.msg?.text ?? JSON.stringify(line.msg ?? line));
                    return <div key={i} style={{ marginBottom: 4 }}>{msg}</div>;
                  })}
                </div>
              </div>
            )}

            <div className="panel" style={{marginBottom: '24px'}}>
              <div className="panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>BACKEND LOGS</span>
                <button type="button" onClick={fetchBackendLogs} disabled={backendLogsLoading} className="btn-scan" style={{ padding: '6px 12px', fontSize: 12 }}>{backendLogsLoading ? 'Refreshing...' : 'Refresh'}</button>
              </div>
              <div style={{ maxHeight: 220, overflow: 'auto', fontFamily: 'monospace', fontSize: 11, background: 'rgba(0,0,0,0.2)', padding: 12, borderRadius: 8 }}>
                {backendLogs.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)' }}>No backend logs yet. Run a scan or click Refresh.</div>
                ) : (
                  backendLogs.map((line, i) => {
                    const msg = line.msg != null && typeof line.msg !== 'object' ? String(line.msg) : (line.msg?.text ?? (line.status && `Status: ${line.status}`) ?? JSON.stringify(line.msg ?? line));
                    return (
                      <div key={i} style={{ marginBottom: 4, color: line.status === 'error' ? 'var(--red)' : line.status === 'done' ? 'var(--green)' : 'var(--text-secondary)' }}>
                        {line.time && <span style={{ opacity: 0.8 }}>{line.time} </span>}
                        {msg}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">VULNERABILITY HEATMAP — 7 DAYS</div>
              <div className="heatmap-days">
                <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
              </div>
              <div className="heatmap-grid">
                <div className="heatmap-cell" style={{backgroundColor: '#20402e'}}></div>
                <div className="heatmap-cell" style={{backgroundColor: '#1c3628'}}></div>
                <div className="heatmap-cell" style={{backgroundColor: '#0F5132'}}></div>
                <div className="heatmap-cell" style={{backgroundColor: '#10B981'}}></div>
                <div className="heatmap-cell" style={{backgroundColor: '#F59E0B'}}></div>
                <div className="heatmap-cell" style={{backgroundColor: '#EF4444'}}></div>
                <div className="heatmap-cell" style={{backgroundColor: '#991B1B'}}></div>
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM SECTIONS */}
        <div className="panel" style={{marginBottom: '24px', position: 'relative'}}>
          <div className="panel-header" style={{border: 'none', display: 'flex', alignItems: 'center'}}>
            <span style={{marginRight: '20px'}}>PROFIT-AT-RISK SIMULATION</span>
            <div style={{height: '1px', flex: 1, backgroundColor: 'var(--border-light)'}}></div>
          </div>
          
          {results?.profit_sims && Object.keys(results.profit_sims).length > 0 ? (
            <>
              <div className="simulation-tabs">
                {Object.entries(results.profit_sims).map(([key, sim]) => (
                  <button key={key} className={`sim-tab-btn ${key === 'ads' ? 'active' : ''}`}>{typeof sim.label === 'string' ? sim.label : String(sim.label ?? '')}</button>
                ))}
              </div>
              <div style={{ marginTop: 16 }}>
                {Object.entries(results.profit_sims).map(([key, sim]) => {
                  const verdictStr = typeof sim.verdict === 'string' ? sim.verdict : (sim.verdict?.text ?? String(sim.verdict ?? ''));
                  return (
                    <div key={key} style={{ marginBottom: 12 }}>
                      <strong>{typeof sim.label === 'string' ? sim.label : String(sim.label ?? '')}</strong> — Net: ₹{(sim.net_profit ?? 0).toLocaleString()} · <span style={{ color: sim.verdictColor }}>{verdictStr}</span>
                      {sim.rows?.length > 0 && (
                        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                          {sim.rows.map((r, i) => (
                            <span key={i} style={{ color: r.color }}>{typeof r.label === 'string' ? r.label : String(r.label ?? '')}: {typeof r.val === 'string' || typeof r.val === 'number' ? r.val : (r.val?.text ?? String(r.val ?? ''))}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <p style={{ color: 'var(--text-muted)', marginTop: 12 }}>Run a scan (with product cost set in Products) to see profit simulations.</p>
          )}
        </div>

        <div className="panel" style={{padding: '0', background: 'transparent', border: 'none'}}>
          <div className="panel-header" style={{border: 'none', display: 'flex', alignItems: 'center', marginBottom: '16px'}}>
            <span style={{marginRight: '20px', display: 'flex', alignItems: 'center', gap: '8px'}}><Users size={14}/> AI PIVOT MEMO — CHIEF STRATEGY OFFICER</span>
            <div style={{height: '1px', flex: 1, backgroundColor: 'var(--border-light)'}}></div>
          </div>

          {results?.pivot_memo ? (
            <div className="memo-cards" style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
              <div className="memo-card rank-1" style={{ padding: 16, background: 'var(--panel-bg)', border: '1px solid var(--border-light)', borderRadius: 8 }}>
                {typeof results.pivot_memo === 'string' ? results.pivot_memo : (results.pivot_memo?.text ?? JSON.stringify(results.pivot_memo))}
              </div>
            </div>
          ) : (
            <div className="empty-state">Run an agent scan to generate the AI pivot memo from the Chief Strategy Officer.</div>
          )}
        </div>

        </>
        )}

        {/* COMPETITORS PAGE */}
        {activeTab === 'COMPETITORS' && (
          <div className="panel">
            <div className="panel-header">ALL COMPETITORS (from last scan)</div>
            {results?.vuln_scores && Object.keys(results.vuln_scores).length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                    <th style={{ textAlign: 'left', padding: 12 }}>Product</th>
                    <th style={{ textAlign: 'left', padding: 12 }}>ASIN</th>
                    <th style={{ textAlign: 'right', padding: 12 }}>Price</th>
                    <th style={{ textAlign: 'right', padding: 12 }}>Rating</th>
                    <th style={{ textAlign: 'right', padding: 12 }}>Score</th>
                    <th style={{ textAlign: 'left', padding: 12 }}>Label</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(results.vuln_scores).map(([asin, v]) => {
                    const p = results?.products?.[asin];
                    return (
                      <tr key={asin} style={{ borderBottom: '1px solid var(--border-light)' }}>
                        <td style={{ padding: 12 }}>{p?.name || asin}</td>
                        <td style={{ padding: 12, fontFamily: 'monospace' }}>{asin}</td>
                        <td style={{ padding: 12, textAlign: 'right' }}>{p?.price != null ? `₹${Number(p.price).toLocaleString()}` : '—'}</td>
                        <td style={{ padding: 12, textAlign: 'right' }}>{p?.rating ?? '—'}</td>
                        <td style={{ padding: 12, textAlign: 'right' }}>{Math.round(v.score)}</td>
                        <td style={{ padding: 12 }}><span className={`badge ${scoreToColorClass(v.score)}`}>{v.label}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">Run an agent scan to see competitor data (real scraped products).</div>
            )}
          </div>
        )}

        {/* PIVOT MEMOS PAGE */}
        {activeTab === 'PIVOT MEMOS' && (
          <div className="panel">
            <div className="panel-header">AI PIVOT MEMO</div>
            {results?.pivot_memo ? (
              <div style={{ whiteSpace: 'pre-wrap', padding: 16, background: 'var(--panel-bg)', borderRadius: 8 }}>{typeof results.pivot_memo === 'string' ? results.pivot_memo : (results.pivot_memo?.text ?? JSON.stringify(results.pivot_memo))}</div>
            ) : (
              <div className="empty-state">Run an agent scan to generate the pivot memo.</div>
            )}
          </div>
        )}

        {/* PROFIT SIM PAGE */}
        {activeTab === 'PROFIT SIM' && (
          <div className="panel">
            <div className="panel-header">PROFIT-AT-RISK SIMULATION</div>
            {results?.profit_sims && Object.keys(results.profit_sims).length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {Object.entries(results.profit_sims).map(([key, sim]) => (
                  <div key={key} style={{ padding: 16, border: '1px solid var(--border-light)', borderRadius: 8 }}>
                    <strong>{typeof sim.label === 'string' ? sim.label : JSON.stringify(sim.label)}</strong>
                    <div style={{ marginTop: 8, color: sim.verdictColor }}>Verdict: {typeof sim.verdict === 'string' ? sim.verdict : (sim.verdict?.text ?? JSON.stringify(sim.verdict ?? ''))}</div>
                    <div style={{ marginTop: 4 }}>Net profit vs baseline: ₹{(sim.net_profit ?? 0).toLocaleString()}</div>
                    {sim.rows?.length > 0 && (
                      <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                        {sim.rows.map((r, i) => (
                          <span key={i} style={{ color: r.color }}>{typeof r.label === 'string' ? r.label : String(r.label)}: {typeof r.val === 'string' || typeof r.val === 'number' ? r.val : (r.val?.text ?? JSON.stringify(r.val ?? ''))}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">Run a scan with product cost set in Products to see profit simulations.</div>
            )}
          </div>
        )}

        {/* REVIEWS / SIGNALS PAGE */}
        {activeTab === 'REVIEWS' && (
          <div className="panel">
            <div className="panel-header">REVIEW SIGNALS (from last scan)</div>
            {results?.signals?.length > 0 ? (
              <div className="signals-list">
                {results.signals.flatMap((sig) => {
                  const name = results?.products?.[sig.asin]?.name || sig.asin;
                  return [
                    <div key={`h-${sig.asin}`} style={{ fontWeight: 600, marginTop: 16, marginBottom: 8 }}>{name}</div>,
                    ...(sig.signals || []).map((s, i) => {
                      const type = typeof s.type === 'string' ? s.type : 'low';
                      const text = typeof s.text === 'string' ? s.text : (s.text?.text ?? JSON.stringify(s.text ?? s));
                      return (
                        <div key={`${sig.asin}-${i}`} className="signal-item">
                          <div className={`signal-dot ${type === 'critical' ? 'red' : type === 'medium' ? 'yellow' : 'green'}`}></div>
                          <div className="signal-text">{text}</div>
                        </div>
                      );
                    })
                  ];
                })}
              </div>
            ) : (
              <div className="empty-state">Run an agent scan to see signals from competitor reviews.</div>
            )}
          </div>
        )}

        {/* ALERTS PAGE */}
        {activeTab === 'ALERTS' && (
          <div className="panel">
            <div className="panel-header">ALERTS BY SEVERITY</div>
            {results?.vuln_scores && Object.keys(results.vuln_scores).length > 0 ? (
              (() => {
                const alerts = Object.entries(results.vuln_scores).filter(([, v]) => v.label === 'Bleeding' || v.label === 'Vulnerable');
                return alerts.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {alerts.map(([asin, v]) => {
                      const name = results?.products?.[asin]?.name || asin;
                      return (
                        <div key={asin} style={{
                          padding: 16,
                          borderLeft: `4px solid ${v.score > 70 ? '#EF4444' : '#F59E0B'}`,
                          background: 'var(--panel-bg)',
                          borderRadius: 8
                        }}>
                          <strong>{name}</strong> ({asin}) — {v.label} (score: {Math.round(v.score)})
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="empty-state">No high-priority alerts. All competitors in Stable or Healthy range.</div>
                );
              })()
            ) : (
              <div className="empty-state">Run an agent scan to see alerts.</div>
            )}
          </div>
        )}

        {/* EMBEDDINGS — stored review vectors in pgvector */}
        {activeTab === 'EMBEDDINGS' && (
          <div className="panel" style={{ maxWidth: 900 }}>
            <div className="panel-header">REVIEW EMBEDDINGS (pgvector)</div>
            <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>
              Stored review text and metadata for each product. Vectors are 1536-dimensional (not shown). Run a scan to populate.
              If you see &quot;Mock review 1&quot;/&quot;Mock review 2&quot;, the product page was scraped but the reviews page returned no text, so fallback text was embedded.
            </p>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
              <input
                type="text"
                className="input-visible"
                value={embeddingsFilterAsin}
                onChange={(e) => setEmbeddingsFilterAsin(e.target.value.trim())}
                placeholder="Filter by ASIN (e.g. B0863TXGM3)"
                style={{ minWidth: 200 }}
              />
              <button className="btn-scan" onClick={fetchEmbeddings} disabled={embeddingsLoading}>
                {embeddingsLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>
            {embeddings.error && <div style={{ color: 'var(--red)', marginBottom: 12 }}>{embeddings.error}</div>}
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>Total: {embeddings.count} embeddings</div>
            <div style={{ maxHeight: 420, overflow: 'auto', border: '1px solid var(--border-light)', borderRadius: 8, background: 'rgba(0,0,0,0.2)' }}>
              {embeddings.embeddings.length === 0 ? (
                <div className="empty-state" style={{ padding: 24 }}>No embeddings yet. Run a scan to scrape and embed reviews.</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                      <th style={{ textAlign: 'left', padding: 10 }}>ID</th>
                      <th style={{ textAlign: 'left', padding: 10 }}>ASIN</th>
                      <th style={{ textAlign: 'left', padding: 10 }}>Review (preview)</th>
                      <th style={{ textAlign: 'left', padding: 10 }}>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {embeddings.embeddings.map((row) => (
                      <tr key={row.id} style={{ borderBottom: '1px solid var(--border-light)' }}>
                        <td style={{ padding: 10, color: 'var(--text-muted)' }}>{row.id}</td>
                        <td style={{ padding: 10 }}><span className="header-pill" style={{ fontSize: 11 }}>{row.asin}</span></td>
                        <td style={{ padding: 10, maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={row.document}>
                          {row.document?.slice(0, 80)}{(row.document?.length > 80) ? '…' : ''}
                        </td>
                        <td style={{ padding: 10, color: 'var(--text-muted)' }}>{row.created_at || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* PRODUCTS / SETTINGS PAGE */}
        {activeTab === 'PRODUCTS' && (
          <div className="panel" style={{ maxWidth: 560 }}>
            <div className="panel-header">PRODUCT CONFIG</div>
            <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>Set your product ASIN and competitor ASINs (Amazon India). The agent will scrape these when you run a scan.</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>Your product ASIN</label>
                <input
                  type="text"
                  className="input-visible"
                  value={productAsin}
                  onChange={(e) => setProductAsin(e.target.value.trim())}
                  placeholder="e.g. B0863TXGM3 or Flipkart FSN / Snapdeal PID"
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>Competitor ASINs (comma-separated)</label>
                <input
                  type="text"
                  className="input-visible"
                  value={competitorAsins}
                  onChange={(e) => setCompetitorAsins(e.target.value.trim())}
                  placeholder="e.g. B0CP54XBWN,B0FC327SXQ or FSN/PID"
                />
              </div>
              {results?.products && Object.keys(results.products).some((a) => results.products[a].fallback_source_id) && (
                <div style={{ fontSize: 12, color: 'var(--brand)', padding: 10, background: 'rgba(245,158,11,0.1)', borderRadius: 8, border: '1px solid var(--border-light)' }}>
                  <strong>Last scan used fallback (use these IDs in the boxes above for Flipkart/Snapdeal):</strong>
                  <ul style={{ margin: '6px 0 0 0', paddingLeft: 18 }}>
                    {Object.entries(results.products)
                      .filter(([, p]) => p.fallback_source_id)
                      .map(([asin, p]) => (
                        <li key={asin}>{asin}: {p.fallback_platform} {p.fallback_platform === 'flipkart' ? 'FSN' : 'PID'} = <code style={{ background: 'rgba(0,0,0,0.2)', padding: '2px 6px', borderRadius: 4 }}>{p.fallback_source_id}</code></li>
                      ))}
                  </ul>
                </div>
              )}
              <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: 12, background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
                <strong style={{ color: 'var(--green)' }}>Good our product / Bad competitor (default — real input):</strong>
                <ul style={{ margin: '8px 0 0 0', paddingLeft: 18 }}>
                  <li>B0863TXGM3 — Sony WH-1000XM4 (our product, premium, good reviews)</li>
                  <li>B0F7LY85KB — boAt Rockerz 421 (competitor, budget, often worse reviews)</li>
                </ul>
                <strong style={{ color: 'var(--text-secondary)', display: 'block', marginTop: 8 }}>More ASINs (earphones/headphones):</strong>
                <ul style={{ margin: '8px 0 0 0', paddingLeft: 18 }}>
                  <li>B0CP54XBWN — boAt Airdopes 91</li>
                  <li>B0FC327SXQ — boAt Rockerz 412</li>
                  <li>B0863TXGM3 — Sony WH-1000XM4</li>
                </ul>
              </div>
              <button className="btn-scan" onClick={() => setActiveTab('INTELLIGENCE')}>
                Go to Intelligence & run scan
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default App;
