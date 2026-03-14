import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { RefreshCw, Copy, Check, ChevronDown, ChevronUp, FileText, BarChart3, AlertTriangle } from 'lucide-react';
import client from '../api/client';
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

/** Clean LLM memo: strip */ /* ** and normalize whitespace */
function cleanMemoText(raw) {
  if (raw == null) return '';
  let s = typeof raw === 'string' ? raw : (raw?.text ?? JSON.stringify(raw));
  return s
    .replace(/\*\//g, '')
    .replace(/\/\*/g, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*\s/g, '• ')
    .replace(/\n\s*\*\s/g, '\n• ')
    .trim();
}

/** Split cleaned memo into milestone paragraphs (by double newline or bullet groups) */
function memoToMilestones(cleaned) {
  if (!cleaned) return [];
  const blocks = cleaned.split(/\n\s*\n+/).map((b) => b.trim()).filter(Boolean);
  return blocks.length ? blocks : [cleaned];
}

function DonutRing({ score, colorClass }) {
  const r = 23;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  return (
    <div className="donut">
      <svg viewBox="0 0 50 50">
        <circle className="donut-bg" cx="25" cy="25" r={r} />
        <circle className={`donut-fill ${colorClass}`} cx="25" cy="25" r={r} strokeDasharray={`${filled} ${circ}`} strokeDashoffset={0} />
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

/** Bar chart: Net impact (₹) for each strategy */
function ProfitBarChart({ profitSims }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  useEffect(() => {
    if (!profitSims || typeof profitSims !== 'object' || !canvasRef.current) return;
    const entries = Object.entries(profitSims).map(([key, sim]) => ({
      label: typeof sim.label === 'string' ? sim.label : key,
      net: Number(sim.net_profit ?? 0),
    }));
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new Chart(canvasRef.current, {
      type: 'bar',
      data: {
        labels: entries.map((e) => e.label),
        datasets: [{
          label: 'Net impact (₹)',
          data: entries.map((e) => e.net),
          backgroundColor: entries.map((e) => e.net >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)'),
          borderColor: entries.map((e) => e.net >= 0 ? '#10B981' : '#EF4444'),
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { ticks: { callback: (v) => '₹' + v } },
        },
      },
    });
    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, [profitSims]);
  return <div style={{ height: 220 }}><canvas ref={canvasRef} /></div>;
}

/** Pie chart: Verdict distribution (Avoid / Safe / Recommended) */
function ProfitPieChart({ profitSims }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  useEffect(() => {
    if (!profitSims || typeof profitSims !== 'object' || !canvasRef.current) return;
    const verdictCounts = {};
    Object.values(profitSims).forEach((sim) => {
      const v = typeof sim.verdict === 'string' ? sim.verdict : String(sim.verdict ?? '');
      verdictCounts[v] = (verdictCounts[v] || 0) + 1;
    });
    const labels = Object.keys(verdictCounts);
    const data = Object.values(verdictCounts);
    const colors = ['#EF4444', '#F59E0B', '#10B981', '#3B82F6'];
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new Chart(canvasRef.current, {
      type: 'pie',
      data: {
        labels,
        datasets: [{ data, backgroundColor: labels.map((_, i) => colors[i % colors.length]) }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } },
      },
    });
    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, [profitSims]);
  return <div style={{ height: 220 }}><canvas ref={canvasRef} /></div>;
}

const TABS = [
  { id: 'strategy', label: 'Strategy & charts', icon: BarChart3 },
  { id: 'competitors', label: 'Competitors & signals', icon: AlertTriangle },
  { id: 'memo', label: 'Pivot memo', icon: FileText },
];

export default function PageIntelligence() {
  const { id: productId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const runId = searchParams.get('run_id');
  const [product, setProduct] = useState(null);
  const [results, setResults] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [backendLogs, setBackendLogs] = useState([]);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('strategy');

  const productAsin = product?.platform_id;
  const hasProfitSims = results?.profit_sims && typeof results.profit_sims === 'object' && Object.keys(results.profit_sims).length > 0;
  const fetchProduct = useCallback(async () => {
    try {
      const { data } = await client.get(`/products/${productId}`);
      setProduct(data);
    } catch (e) {
      setProduct(null);
    }
  }, [productId]);

  const fetchResult = useCallback(async (rid) => {
    try {
      const { data } = await client.get(`/job/${rid}/result`);
      if (data.status === 'success') setResults(data);
      else setResults(null); // running / error / pending — no results yet
    } catch (e) {
      setResults(null);
      if (e.response?.status === 404) setSearchParams({}); // clear run_id so we stop requesting missing run
    }
  }, []);

  const fetchBackendLogs = useCallback(async () => {
    try {
      const { data } = await client.get('/logs?limit=100');
      setBackendLogs(data.lines || []);
    } catch (e) {
      setBackendLogs([]);
    }
  }, []);

  useEffect(() => {
    fetchProduct();
  }, [fetchProduct]);

  useEffect(() => {
    if (!productId) return;
    client.get(`/scan/${productId}/history?limit=5`).then(({ data }) => {
      const runs = data.runs || [];
      setHistory(runs);
      // Auto-select latest run when none selected so sections show data
      if (!runId && runs.length > 0) setSearchParams({ run_id: runs[0].run_id });
    }).catch(() => {});
  }, [productId]);

  useEffect(() => {
    if (runId) fetchResult(runId);
    else setResults(null);
  }, [runId, fetchResult]);

  useEffect(() => {
    if (runId) fetchBackendLogs();
  }, [runId, fetchBackendLogs]);

  useEffect(() => {
    if (!scanning) return;
    const interval = setInterval(fetchBackendLogs, 8000);
    return () => clearInterval(interval);
  }, [scanning, fetchBackendLogs]);

  const handleRunScan = async () => {
    if (scanning) return;
    setScanning(true);
    setLogs([]);
    try {
      const { data } = await client.post(`/scan/${productId}`);
      const rid = data.run_id;
      setSearchParams({ run_id: rid });
      const token = localStorage.getItem('ps_token');
      const streamUrl = token ? `/api/job/${rid}/stream?token=${encodeURIComponent(token)}` : `/api/job/${rid}/stream`;
      const es = new EventSource(streamUrl);
      es.onmessage = (event) => {
        const d = JSON.parse(event.data);
        setLogs((prev) => [...prev, d]);
        if (d.status === 'done' || d.status === 'error') {
          es.close();
          setScanning(false);
          if (d.status === 'done') fetchResult(rid);
          fetchBackendLogs();
        }
      };
      es.onerror = () => {
        es.close();
        setScanning(false);
        fetchResult(rid);
        fetchBackendLogs();
      };
    } catch (e) {
      setScanning(false);
    }
  };

  if (!product) return <div className="main-content"><div className="empty-state">Loading…</div></div>;

  return (
    <div className="main-content">
      <nav className="breadcrumb">
        <Link to="/products">Products</Link>
        <span>/</span>
        <Link to={`/products/${productId}`}>{product.product_name}</Link>
        <span>/</span>
        <span>Analysis</span>
      </nav>
      <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div className="header-subtitle">MONITORING PRODUCT</div>
          <h1 className="header-title">
            {product.product_name} <span className="header-pill">{product.platform_id}</span>
          </h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link to={`/products/${productId}`} className="btn-secondary">Back to product</Link>
          <button className={`btn-scan ${scanning ? 'scanning' : ''}`} onClick={handleRunScan} disabled={scanning}>
            <RefreshCw size={14} className={scanning ? 'animate-pulse' : ''} />
            {scanning ? 'Running…' : 'Run New Scan'}
          </button>
        </div>
      </div>
      {history.length > 0 && (
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span className="muted">Last runs:</span>
          {history.slice(0, 5).map((r) => (
            <button key={r.run_id} type="button" className={runId === r.run_id ? 'badge blue' : 'btn-secondary'} style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => setSearchParams({ run_id: r.run_id })}>
              {new Date(r.created_at).toLocaleString()} ({r.status})
            </button>
          ))}
        </div>
      )}

      <div className="metrics-row">
        <div className="metric-card">
          <div className="metric-title">YOUR PRICE</div>
          <div className="metric-value white">
            {product.price != null ? `₹${Number(product.price).toLocaleString()}` : (results?.products?.[productAsin]?.price != null ? `₹${Number(results.products[productAsin].price).toLocaleString()}` : '—')}
          </div>
          <div className="metric-subtitle">Seller listed price</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">MARGIN AT RISK</div>
          <div className="metric-value red">
            {results?.profit_sims?.match?.net_profit != null ? `₹${Math.abs(results.profit_sims.match.net_profit).toLocaleString()}` : '—'}
          </div>
          <div className="metric-subtitle">If matched comp price</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">PIVOT UPSIDE</div>
          <div className="metric-value green">
            {results?.profit_sims?.ads?.net_profit != null && results.profit_sims.ads.net_profit > 0 ? `+₹${results.profit_sims.ads.net_profit.toLocaleString()}` : '—'}
          </div>
          <div className="metric-subtitle">Best strategy net gain</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">SIGNALS DETECTED</div>
          <div className="metric-value yellow">
            {results?.signals ? results.signals.reduce((n, s) => n + (s.signals?.length || 0), 0) : '—'}
          </div>
          <div className="metric-subtitle">{results?.signals?.length ? `${results.signals.length} competitor(s)` : 'Run scan'}</div>
        </div>
      </div>

      {/* Tabs: avoid overlap; one view at a time */}
      <div className="analysis-tabs">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`analysis-tab ${activeTab === id ? 'active' : ''}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      <div className="analysis-tab-content">
        {activeTab === 'strategy' && (
          <>
            <section className="panel profit-at-risk-panel" aria-label="Profit at risk simulation">
              <div className="panel-header" style={{ marginTop: 0 }}>
                PROFIT-AT-RISK SIMULATION
                <span className="muted" style={{ fontWeight: 400, fontSize: 11, marginLeft: 8 }}>Match vs Hold vs Ad Campaign</span>
              </div>
              {hasProfitSims ? (
                <>
                  <div className="profit-sim-grid">
                    {Object.entries(results.profit_sims).map(([key, sim]) => {
                      const verdictStr = typeof sim.verdict === 'string' ? sim.verdict : (sim.verdict?.text ?? String(sim.verdict ?? ''));
                      const labelStr = typeof sim.label === 'string' ? sim.label : String(sim.label ?? '');
                      const net = sim.net_profit ?? 0;
                      const isPositive = net > 0;
                      const isNegative = net < 0;
                      return (
                        <div key={key} className="profit-sim-card">
                          <div className="profit-sim-card-header">
                            <span className="profit-sim-label">{labelStr}</span>
                            <span className="profit-sim-verdict" style={{ color: sim.verdictColor || 'var(--text-secondary)' }}>{verdictStr}</span>
                          </div>
                          <div className={`profit-sim-net ${isPositive ? 'positive' : isNegative ? 'negative' : ''}`}>
                            {isPositive ? '+' : ''}₹{Number(net).toLocaleString()}
                          </div>
                          <div className="profit-sim-net-label">Net impact vs baseline</div>
                          {sim.rows?.length > 0 && (
                            <ul className="profit-sim-rows">
                              {sim.rows.map((r, i) => (
                                <li key={i} style={{ color: r.color || 'var(--text-secondary)' }}>
                                  <span className="profit-sim-row-label">{typeof r.label === 'string' ? r.label : String(r.label ?? '')}</span>
                                  <span className="profit-sim-row-val">{typeof r.val === 'string' || typeof r.val === 'number' ? r.val : (r.val?.text ?? String(r.val ?? ''))}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <div className="profit-charts-row">
                    <div className="panel" style={{ flex: 1, minWidth: 0 }}>
                      <div className="panel-header">Net impact by strategy (bar)</div>
                      <ProfitBarChart profitSims={results.profit_sims} />
                    </div>
                    <div className="panel" style={{ flex: 1, minWidth: 0 }}>
                      <div className="panel-header">Verdict distribution (pie)</div>
                      <ProfitPieChart profitSims={results.profit_sims} />
                    </div>
                  </div>
                </>
              ) : (
                <div className="profit-sim-empty">
                  <p>Run a scan to see profit-at-risk simulations.</p>
                  <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>Compare Match Price, Hold Price, and Ad Campaign strategies.</p>
                </div>
              )}
            </section>
          </>
        )}

        {activeTab === 'competitors' && (
          <div className="dashboard-grid dashboard-grid-single">
            <div className="panel" style={{ marginBottom: 24 }}>
              <div className="panel-header">COMPETITOR VULNERABILITY</div>
              <div className="competitor-list">
                {results?.vuln_scores && typeof results.vuln_scores === 'object' && Object.keys(results.vuln_scores).length > 0 ? (
                  Object.entries(results.vuln_scores).map(([asin, v]) => {
                    const p = results?.products?.[asin];
                    const name = p?.name || `Competitor ${asin}`;
                    const isBleeding = v.bleeding === true;
                    const bleedReason = v.bleeding_reason === 'low_rating' ? 'Low rating' : (v.bleeding_reason === 'high_vulnerability' ? 'High vulnerability' : null);
                    return (
                      <div key={asin} className={`competitor-item ${isBleeding ? 'competitor-bleeding' : ''}`}>
                        <div className="comp-info">
                          <h4>{name}</h4>
                          <span className="comp-desc">
                            {asin}{p?.review_count != null ? ` · ${p.review_count} reviews` : ''}
                            {v.rating != null && ` · ${v.rating}★`}
                          </span>
                          {isBleeding && (
                            <span className="badge bleeding-badge" title={bleedReason || 'Negative impact'}>
                              BLEEDING{bleedReason ? ` · ${bleedReason}` : ''}
                            </span>
                          )}
                        </div>
                        <div className="comp-stats">
                          {p?.price != null && <div className="comp-price-row">₹{Number(p.price).toLocaleString()}</div>}
                          <div className={`badge ${scoreToColorClass(v.score)}`}>{Math.round(v.score)} · {(v.label || 'N/A').toUpperCase()}</div>
                        </div>
                        <DonutRing score={v.score} colorClass={scoreToColorClass(v.score)} />
                      </div>
                    );
                  })
                ) : (
                  <div className="empty-state">No competitor data yet. Run a scan.</div>
                )}
              </div>
            </div>
            <div className="panel" style={{ marginBottom: 24 }}>
              <div className="panel-header">REVIEW SIGNALS</div>
              <div className="signals-list">
                {Array.isArray(results?.signals) && results.signals.length > 0 ? (
                  results.signals.flatMap((sig) =>
                    (sig.signals || []).map((s, i) => {
                      const type = typeof s.type === 'string' ? s.type : 'low';
                      const text = typeof s.text === 'string' ? s.text : (s.text?.text ?? JSON.stringify(s.text ?? s));
                      return (
                        <div key={`${sig.asin}-${i}`} className="signal-item">
                          <div className={`signal-dot ${type === 'critical' ? 'red' : type === 'medium' ? 'yellow' : 'green'}`} />
                          <div className="signal-text">{text}</div>
                        </div>
                      );
                    })
                  )
                ) : (
                  <div className="empty-state">Run a scan to see signals.</div>
                )}
              </div>
            </div>
            {logs.length > 0 && (
              <div className="panel" style={{ marginBottom: 24 }}>
                <div className="panel-header">AGENT LOG (live)</div>
                <div className="agent-log" style={{ maxHeight: 200, overflow: 'auto', fontFamily: 'monospace', fontSize: 12 }}>
                  {logs.map((line, i) => {
                    const msg = line.msg != null && typeof line.msg !== 'object' ? String(line.msg) : (line.msg?.text ?? JSON.stringify(line.msg ?? line));
                    return <div key={i} style={{ marginBottom: 4 }}>{msg}</div>;
                  })}
                </div>
              </div>
            )}
            <div className="panel" style={{ marginBottom: 24 }}>
              <div className="panel-header">BACKEND LOGS</div>
              <div style={{ maxHeight: 220, overflow: 'auto', fontFamily: 'monospace', fontSize: 11, background: 'rgba(0,0,0,0.2)', padding: 12, borderRadius: 8 }}>
                {backendLogs.length === 0 ? <div style={{ color: 'var(--text-muted)' }}>No logs yet.</div> : backendLogs.map((line, i) => {
                  const msg = line.msg != null && typeof line.msg !== 'object' ? String(line.msg) : (line.msg?.text ?? (line.status && `Status: ${line.status}`) ?? JSON.stringify(line.msg ?? line));
                  return (
                    <div key={i} style={{ marginBottom: 4, color: line.status === 'error' ? 'var(--red)' : line.status === 'done' ? 'var(--green)' : 'var(--text-secondary)' }}>
                      {line.time && <span style={{ opacity: 0.8 }}>{line.time} </span>}{msg}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'memo' && (
          <PivotMemoSection memo={results?.pivot_memo} />
        )}
      </div>
    </div>
  );
}

function PivotMemoSection({ memo }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const cleaned = cleanMemoText(memo);
  const milestones = memoToMilestones(cleaned);

  const handleCopy = () => {
    if (!cleaned) return;
    navigator.clipboard.writeText(cleaned).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!memo) {
    return (
      <div className="panel pivot-memo-section" style={{ marginTop: 32 }}>
        <div className="panel-header pivot-memo-header">
          <FileText size={18} />
          <span>AI PIVOT MEMO</span>
        </div>
        <div className="empty-state">Run a scan to generate the pivot memo.</div>
      </div>
    );
  }

  return (
    <div className="panel pivot-memo-section" style={{ marginTop: 32 }}>
      <div
        className="panel-header pivot-memo-header"
        style={{ cursor: 'pointer', userSelect: 'none', flexWrap: 'wrap', gap: 12 }}
        onClick={() => setExpanded((e) => !e)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setExpanded((x) => !x)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <FileText size={18} />
          <span>AI PIVOT MEMO</span>
          <span className="muted" style={{ fontSize: 12 }}>({milestones.length} section{milestones.length !== 1 ? 's' : ''})</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            className="btn-secondary"
            style={{ padding: '6px 10px', fontSize: 12 }}
            onClick={(e) => { e.stopPropagation(); handleCopy(); }}
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? ' Copied' : ' Copy'}
          </button>
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </div>
      {expanded && (
        <div className="pivot-memo-milestones">
          {milestones.map((block, i) => (
            <div key={i} className="pivot-milestone">
              <div className="pivot-milestone-marker" aria-hidden>
                <span className="pivot-milestone-num">{i + 1}</span>
              </div>
              <div className="pivot-milestone-content">
                <div className="pivot-milestone-text" style={{ whiteSpace: 'pre-wrap' }}>
                  {block}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
