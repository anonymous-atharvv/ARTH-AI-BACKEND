export interface Transaction {
  id: string;
  amount: number;
  type: 'income' | 'expense' | 'transfer';
  category_code: string | null;
  counterparty: string | null;
  description: string | null;
  payment_method: string;
  transaction_date: string;
  source: 'image' | 'voice' | 'text' | 'upi_statement' | 'manual';
  verified: boolean;
  confidence_score: number | null;
  created_at: string | null;
}

export interface ArthScore {
  score: number;
  grade: string;
  grade_hi: string;
  factors: Record<string, number>;
  max_loan_eligible: number;
  data_points: number;
  period_days: number;
  insight_hi: string;
  insight_en: string;
  calculated_at: string;
}

export interface DashboardSummary {
  mtd_income: number;
  mtd_expenses: number;
  mtd_net_profit: number;
  mtd_margin_pct: number;
  wtd_income: number;
  wtd_expenses: number;
  wtd_net: number;
  avg_daily_income: number;
  days_active_mtd: number;
  top_income_category: string | null;
  top_expense_category: string | null;
  income_by_category: Record<string, number>;
  expense_by_category: Record<string, number>;
  total_transactions: number;
}

export interface PnlData {
  period: string;
  total_income: number;
  total_expenses: number;
  net_profit: number;
  net_margin_pct: number;
  series: PnlSeriesItem[];
  top_income_categories: CategoryAmount[];
  top_expense_categories: CategoryAmount[];
}

export interface PnlSeriesItem {
  period_label: string;
  income: number;
  expenses: number;
  net: number;
}

export interface CategoryAmount {
  code: string;
  amount: number;
}

export interface LoanOffer {
  name: string;
  logo: string;
  interest_rate_pct: number;
  max_loan: number;
  loan_amount: number;
  emi_per_month: number;
  tenure_months: number[];
  tagline: string;
  turnaround_hours: number;
  eligible: boolean;
}

export const CATEGORY_META: Record<string, { name: string; nameHi: string; icon: string; color: string }> = {
  sales_product: { name: 'Product Sales', nameHi: 'माल बिक्री', icon: '🛒', color: '#16a34a' },
  sales_service: { name: 'Service Income', nameHi: 'सेवा आय', icon: '⚙️', color: '#059669' },
  commission: { name: 'Commission', nameHi: 'कमीशन', icon: '🤝', color: '#10b981' },
  inventory: { name: 'Inventory', nameHi: 'माल/स्टॉक', icon: '📦', color: '#ef4444' },
  labor_wages: { name: 'Labor/Wages', nameHi: 'मजदूरी', icon: '👷', color: '#f97316' },
  transport_fuel: { name: 'Transport/Fuel', nameHi: 'ईंधन', icon: '⛽', color: '#eab308' },
  rent_premises: { name: 'Rent', nameHi: 'किराया', icon: '🏪', color: '#8b5cf6' },
  utilities: { name: 'Utilities', nameHi: 'बिजली/पानी', icon: '💡', color: '#6366f1' },
  equipment: { name: 'Equipment', nameHi: 'उपकरण', icon: '🔧', color: '#ec4899' },
  marketing: { name: 'Marketing', nameHi: 'विज्ञापन', icon: '📢', color: '#14b8a6' },
  food_personal: { name: 'Food', nameHi: 'खाना', icon: '🍱', color: '#f59e0b' },
  mobile_internet: { name: 'Mobile/Internet', nameHi: 'मोबाइल', icon: '📱', color: '#3b82f6' },
  other_income: { name: 'Other Income', nameHi: 'अन्य आय', icon: '💵', color: '#22c55e' },
  other_expense: { name: 'Other Expense', nameHi: 'अन्य खर्च', icon: '📝', color: '#94a3b8' },
};

export const SOURCE_ICONS: Record<string, string> = {
  image: '📸',
  voice: '🎤',
  text: '✍️',
  upi_statement: '📱',
  manual: '✏️',
};
