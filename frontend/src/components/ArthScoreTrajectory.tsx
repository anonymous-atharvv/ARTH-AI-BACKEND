import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useLanguage } from '../contexts/LanguageContext';
import './ArthScoreTrajectory.css';

interface HistoryItem {
  score: number;
  grade: string;
  date: string;
  data_points: number;
}

interface Props {
  history: HistoryItem[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  const { t } = useLanguage();
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload;
  return (
    <div className="trajectory-tooltip">
      <p className="tooltip-date">{label}</p>
      <p className="tooltip-score">{t('Score', 'स्कोर')}: <span>{data.score}</span></p>
      <p className="tooltip-grade">{t('Grade', 'श्रेणी')}: {t(data.grade, data.grade)}</p>
      <p className="tooltip-datapoints">{t('Data Points', 'डेटा अंक')}: {data.data_points}</p>
    </div>
  );
};

export default function ArthScoreTrajectory({ history }: Props) {
  const { t } = useLanguage();
  return (
    <div className="trajectory-card">
      <div className="trajectory-header">
        <h3 className="trajectory-title">🎯 {t('ArthScore™ Trajectory', 'ArthScore™ प्रक्षेपवक्र')}</h3>
        <span className="trajectory-subtitle">{t('Credit health trend', 'क्रेडिट स्वास्थ्य प्रवृत्ति')}</span>
      </div>
      <div className="trajectory-chart-wrapper">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={history} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={{ stroke: '#334155' }} />
            <YAxis domain={[300, 900]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={{ stroke: '#334155' }} />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#6366f1"
              strokeWidth={3}
              activeDot={{ r: 6, fill: '#6366f1' }}
              dot={{ r: 4, stroke: '#6366f1', strokeWidth: 2, fill: '#0f172a' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
