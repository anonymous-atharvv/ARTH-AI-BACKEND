import type { Transaction } from '../types';
import { CATEGORY_META, SOURCE_ICONS } from '../types';
import './TransactionFeed.css';

interface Props {
  transactions: Transaction[];
  limit?: number;
}

export default function TransactionFeed({ transactions, limit }: Props) {
  const items = limit ? transactions.slice(0, limit) : transactions;

  return (
    <div className="feed-card">
      <div className="feed-header">
        <h3 className="feed-title">💳 Recent Transactions</h3>
        <span className="feed-count">{transactions.length} total</span>
      </div>
      <div className="feed-list">
        {items.map((tx) => {
          const cat = CATEGORY_META[tx.category_code || 'other_expense'];
          const isIncome = tx.type === 'income';
          return (
            <div key={tx.id} className="feed-item">
              <div className="feed-icon" style={{ background: `${cat?.color || '#64748b'}20` }}>
                {cat?.icon || '💰'}
              </div>
              <div className="feed-details">
                <div className="feed-desc">{tx.description || tx.counterparty || 'Transaction'}</div>
                <div className="feed-meta">
                  <span>{cat?.name || tx.category_code}</span>
                  <span className="feed-dot">•</span>
                  <span>{new Date(tx.transaction_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                  <span className="feed-dot">•</span>
                  <span>{SOURCE_ICONS[tx.source] || '📝'} {tx.source}</span>
                </div>
              </div>
              <div className={`feed-amount ${isIncome ? 'income' : 'expense'}`}>
                {isIncome ? '+' : '-'}₹{tx.amount.toLocaleString('en-IN')}
              </div>
            </div>
          );
        })}
        {items.length === 0 && (
          <div className="feed-empty">No transactions yet. Send a receipt to ArthAI! 📸</div>
        )}
      </div>
    </div>
  );
}
