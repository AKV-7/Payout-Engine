import React, { useState, useEffect } from 'react';
import { getMerchant, getTransactions } from '../api';

function Dashboard({ merchantId }) {
  const [merchant, setMerchant] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    if (!merchantId) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const [merchantRes, txRes] = await Promise.all([
        getMerchant(),
        getTransactions(),
      ]);
      setMerchant(merchantRes.data);
      setTransactions(txRes.data.results || txRes.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [merchantId]);

  if (loading && !merchant) {
    return (
      <div className="flex items-center justify-center py-20 border border-zinc-200 rounded-xl bg-white shadow-sm">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-zinc-900"></div>
          <p className="text-[13px] font-medium text-zinc-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!merchantId) {
    return (
      <div className="flex items-center justify-center py-20 border border-zinc-200 rounded-xl bg-white shadow-sm">
        <p className="text-[14px] font-medium text-zinc-500">Please enter a merchant ID to view the dashboard.</p>
      </div>
    );
  }

  if (!merchantId) {
    return (
      <div className="flex items-center justify-center py-20 border border-zinc-200 rounded-xl bg-white shadow-sm">
        <div className="flex flex-col items-center gap-3">
          <svg className="w-8 h-8 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-[14px] font-medium text-zinc-600">Enter a merchant ID to view dashboard</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50/50 border border-red-200 text-red-700 px-5 py-4 rounded-xl shadow-sm">
        <div className="flex items-center gap-3">
          <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-[14px] font-medium">Failed to load dashboard</p>
        </div>
      </div>
    );
  }

  const available = merchant?.available_balance || 0;
  const held = merchant?.held_balance || 0;
  const total = available + held;

  const formatMoney = (paise) => {
    const rupees = paise / 100;
    return `₹${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const cards = [
    { label: 'Available balance', amount: available, type: 'available' },
    { label: 'Held balance', amount: held, type: 'held' },
    { label: 'Total balance', amount: total, type: 'total' },
  ];

  return (
    <div className="space-y-6">
      {/* Balance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {cards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl shadow-sleek border border-zinc-200 overflow-hidden flex flex-col justify-between">
            <div className="px-5 pt-5 pb-2">
               <div className="flex items-center justify-between mb-3">
                  <p className="text-[13px] font-medium text-zinc-500">{card.label}</p>
                  {card.type === 'available' && <div className="w-2 h-2 rounded-full bg-emerald-500"></div>}
                  {card.type === 'held' && <div className="w-2 h-2 rounded-full bg-amber-400"></div>}
                  {card.type === 'total' && <div className="w-2 h-2 rounded-full bg-zinc-800"></div>}
                </div>
              <p className="text-3xl font-semibold tracking-tight text-zinc-900">{formatMoney(card.amount)}</p>
            </div>
            <div className="px-5 pb-5 mt-1">
              <p className="text-[13px] text-zinc-400">
                {card.type === 'available' ? 'Ready to withdraw' : 
                 card.type === 'held' ? 'Pending payouts' : 'Total funds'}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Transactions */}
      <div className="bg-white rounded-xl shadow-sleek border border-zinc-200 overflow-hidden">
        <div className="border-b border-zinc-100 px-5 py-4 flex items-center justify-between bg-zinc-50/50">
           <h3 className="text-[14px] font-medium text-zinc-900">Ledger Activity</h3>
           <span className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider">Last 10 entries</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[14px]">
            <thead className="bg-zinc-50/30 border-b border-zinc-100">
              <tr>
                <th className="px-5 py-2.5 font-medium text-zinc-500 w-[120px]">Type</th>
                <th className="px-5 py-2.5 font-medium text-zinc-500">Amount</th>
                <th className="px-5 py-2.5 font-medium text-zinc-500">Description</th>
                <th className="px-5 py-2.5 font-medium text-zinc-500 text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {transactions.slice(0, 10).map((tx) => (
                <tr key={tx.id} className="hover:bg-zinc-50/50 transition-colors group">
                  <td className="px-5 py-3.5 align-middle">
                 <span className={`inline-flex flex-row items-center gap-1.5 text-[12px] font-medium ${
                       tx.type === 'credit'
                         ? 'text-emerald-700'
                         : 'text-zinc-600'
                     }`}>
                       {tx.type === 'credit' ? (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>
                      ) : (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-zinc-400"><path d="m19 12-7 7-7-7"/><path d="M12 5v14"/></svg>
                      )}
                      {tx.type === 'credit' ? 'Credit' : 'Debit'}
                    </span>
                  </td>
                   <td className="px-5 py-3.5 align-middle font-medium text-zinc-900">
                     {tx.type === 'credit' ? '+' : '-'}{formatMoney(tx.amount_paise)}
                  </td>
                  <td className="px-5 py-3.5 align-middle text-zinc-600 truncate max-w-[200px]">{tx.description}</td>
                  <td className="px-5 py-3.5 align-middle text-zinc-400 tabular-nums text-right">
                    {new Date(tx.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })}
                  </td>
                </tr>
              ))}
              {transactions.length === 0 && (
                <tr>
                  <td colSpan="4" className="px-5 py-12 text-center">
                    <p className="text-[14px] text-zinc-400">No transactions recorded yet.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
} // ← This closes the Dashboard function

export default Dashboard;
