import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { PnlSeriesItem } from '../types';
import './PLChart.css';

interface Props {
  data: PnlSeriesItem[];
  period: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload) return null;
  return (
    <div className="pnl-tooltip">
      <p className="tooltip-label">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: ₹{Number(p.value).toLocaleString('en-IN')}
        </p>
      ))}
    </div>
  );
};

export default function PLChart({ data, period }: Props) {
  return (
    <div className="pnl-card">
      <div className="pnl-header">
        <h3 className="pnl-title">📈 Profit & Loss</h3>
        <span className="pnl-period">{period}</span>
      </div>
      <div className="pnl-chart-wrapper">
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4ade80" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#4ade80" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="period_label" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={{ stroke: '#334155' }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={{ stroke: '#334155' }}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 10 }} />
            <Area type="monotone" dataKey="income" stroke="#4ade80" fill="url(#incomeGrad)"
              strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: '#4ade80' }} name="Income" />
            <Area type="monotone" dataKey="expenses" stroke="#f87171" fill="url(#expenseGrad)"
              strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: '#f87171' }} name="Expenses" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
