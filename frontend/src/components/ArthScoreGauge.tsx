import './ArthScoreGauge.css';

interface Props {
  score: number;
  grade: string;
  maxLoan: number;
  animate?: boolean;
  calculatedAt?: string;
  dataPoints?: number;
}

export default function ArthScoreGauge({
  score,
  grade,
  maxLoan,
  animate = true,
  calculatedAt,
  dataPoints
}: Props) {
  const min = 300, max = 900;
  const pct = Math.max(0, Math.min(1, (score - min) / (max - min)));
  const getColor = () => {
    if (score >= 750) return '#16a34a';
    if (score >= 650) return '#eab308';
    if (score >= 550) return '#f97316';
    return '#ef4444';
  };

  const r = 90, cx = 120, cy = 120;
  const startAngle = -225, endAngle = 45;
  const describeArc = (sa: number, ea: number) => {
    const s = (sa * Math.PI) / 180, e = (ea * Math.PI) / 180;
    const x1 = cx + r * Math.cos(s), y1 = cy + r * Math.sin(s);
    const x2 = cx + r * Math.cos(e), y2 = cy + r * Math.sin(e);
    const large = ea - sa > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  };
  const filledEnd = startAngle + pct * (endAngle - startAngle);

  const confidence = dataPoints === undefined ? 'Unknown' : dataPoints >= 20 ? 'High' : dataPoints >= 10 ? 'Medium' : 'Low';
  const confidenceColor = confidence === 'High' ? '#4ade80' : confidence === 'Medium' ? '#facc15' : '#f87171';

  return (
    <div className="arth-gauge-card">
      <div className="gauge-header">
        <span className="gauge-logo">📊</span>
        <span className="gauge-title">ArthScore™</span>
      </div>
      <svg viewBox="0 0 240 160" className={`gauge-svg ${animate ? 'animate' : ''}`}>
        <path d={describeArc(startAngle, endAngle)} fill="none" stroke="#1e293b" strokeWidth="14" strokeLinecap="round" />
        <path d={describeArc(startAngle, filledEnd)} fill="none" stroke={getColor()} strokeWidth="14" strokeLinecap="round"
          className="gauge-fill" style={{ '--target-end': filledEnd } as React.CSSProperties} />
        <text x={cx} y={cy - 5} textAnchor="middle" className="gauge-score" fill="white">{score}</text>
        <text x={cx} y={cy + 18} textAnchor="middle" className="gauge-max" fill="#64748b">/900</text>
      </svg>
      <div className="gauge-grade" style={{ color: getColor() }}>{grade}</div>
      <div className="gauge-loan">
        <span className="loan-label">Loan Eligible</span>
        <span className="loan-amount" style={{ color: getColor() }}>₹{maxLoan.toLocaleString('en-IN')}</span>
      </div>
      {(dataPoints !== undefined || calculatedAt) && (
        <div className="gauge-meta">
          <div className="meta-row">
            <span>Confidence:</span>
            <span style={{ color: confidenceColor, fontWeight: 700 }}>{confidence}</span>
          </div>
          {dataPoints !== undefined && dataPoints !== null && (
            <div className="meta-row">
              <span>Data Points:</span>
              <span style={{ color: '#e2e8f0' }}>{dataPoints}</span>
            </div>
          )}
          {calculatedAt && (
            <div className="meta-row">
              <span>Updated:</span>
              <span style={{ color: '#94a3b8' }}>{calculatedAt}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
