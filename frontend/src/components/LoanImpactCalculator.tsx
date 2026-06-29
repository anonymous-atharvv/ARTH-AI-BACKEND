import { useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import './LoanImpactCalculator.css';

interface Props {
  maxLoan: number;
  score: number;
  actualSurplus: number;
}

export default function LoanImpactCalculator({ maxLoan, score, actualSurplus }: Props) {
  const { t } = useLanguage();
  const [loanAmount, setLoanAmount] = useState(Math.min(50000, maxLoan));
  const [tenureMonths, setTenureMonths] = useState(12);

  // Interest rate varies by score (750+ gets 14%, 700 gets 16%, etc.)
  const getInterestRate = (s: number) => {
    if (s >= 800) return 12;
    if (s >= 750) return 14;
    if (s >= 700) return 16;
    if (s >= 650) return 18;
    return 22;
  };

  const annualRate = getInterestRate(score);
  const monthlyRate = annualRate / 12 / 100;
  
  // EMI Formula = [P x R x (1+R)^N]/[((1+R)^N)-1]
  const emi = Math.round(
    (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, tenureMonths)) /
    (Math.pow(1 + monthlyRate, tenureMonths) - 1)
  );

  const totalPayment = emi * tenureMonths;
  const totalInterest = totalPayment - loanAmount;

  const surplus = actualSurplus;
  const surplusPct = surplus > 0 ? Math.round((emi / surplus) * 100) : 100;
  const isSafe = surplus > 0 && surplusPct <= 35;

  return (
    <div className="calc-card">
      <h3 className="calc-title">🧮 {t('Loan Impact Simulator', 'ऋण प्रभाव सिमुलेटर')}</h3>
      <p className="calc-subtitle">
        {t('Understand how a micro-loan fits into your current business cash flows.', 'समझें कि एक छोटा ऋण आपके वर्तमान व्यावसायिक नकदी प्रवाह में कैसे फिट बैठता है।')}
      </p>

      <div className="calc-slider-group">
        <div className="slider-label-row">
          <span>{t('Loan Amount', 'ऋण राशि')}</span>
          <span className="slider-value">₹{loanAmount.toLocaleString('en-IN')}</span>
        </div>
        <input
          type="range"
          min={10000}
          max={Math.max(20000, maxLoan)}
          step={5000}
          value={loanAmount}
          onChange={(e) => setLoanAmount(Number(e.target.value))}
          className="calc-slider"
        />
        <div className="slider-range">
          <span>₹10,000</span>
          <span>Max: ₹{maxLoan.toLocaleString('en-IN')}</span>
        </div>
      </div>

      <div className="calc-slider-group">
        <div className="slider-label-row">
          <span>{t('Tenure (Months)', 'अवधि (महीने)')}</span>
          <span className="slider-value">{tenureMonths} months</span>
        </div>
        <input
          type="range"
          min={3}
          max={24}
          step={3}
          value={tenureMonths}
          onChange={(e) => setTenureMonths(Number(e.target.value))}
          className="calc-slider"
        />
        <div className="slider-range">
          <span>3 months</span>
          <span>24 months</span>
        </div>
      </div>

      <div className="calc-results">
        <div className="calc-result-item">
          <span className="calc-result-label">{t('Estimated EMI', 'अनुमानित ईएमआई')}</span>
          <span className="calc-result-value accent">₹{emi.toLocaleString('en-IN')} / mo</span>
        </div>
        <div className="calc-result-item">
          <span className="calc-result-label">{t('Interest Rate', 'ब्याज दर')}</span>
          <span className="calc-result-value">{annualRate}% p.a.</span>
        </div>
        <div className="calc-result-item">
          <span className="calc-result-label">{t('Total Interest', 'कुल ब्याज')}</span>
          <span className="calc-result-value">₹{totalInterest.toLocaleString('en-IN')}</span>
        </div>
      </div>

      <div className="calc-affordability">
        <div className={`affordability-indicator ${isSafe ? 'safe' : 'danger'}`}>
          <span className={`dot ${isSafe ? 'safe' : 'danger'}`}></span>
          <span className="aff-text">
            {t(
              `EMI represents ~${surplusPct}% of your monthly P&L surplus (${isSafe ? 'Safe level!' : 'High debt load!'})`,
              `ईएमआई आपके मासिक अधिशेष का ~${surplusPct}% है (${isSafe ? 'सुरक्षित स्तर!' : 'उच्च ऋण भार!'})`
            )}
          </span>
        </div>
      </div>
    </div>
  );
}
