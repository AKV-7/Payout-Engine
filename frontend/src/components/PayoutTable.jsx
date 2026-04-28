import React, { useState, useEffect } from 'react';
import api from '../api';

function PayoutTable({ merchantId }) {
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPayouts = async () => {
    if (!merchantId) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.get('/payouts/');
      setPayouts(res.data.results || res.data);
    } catch (err) {
      console.error('Failed to fetch payouts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayouts();
    const interval = setInterval(fetchPayouts, 3000);
    return () => clearInterval(interval);
  }, [merchantId]);

  const formatMoney = (paise) => {
    const rupees = paise / 100;
    return `₹ ${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getStatusConfig = (status) => {
    const configs = {
      pending: { bg: 'bg-zinc-100', text: 'text-zinc-600', dot: 'bg-zinc-400', label: 'Pending' },
      processing: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500', label: 'Processing' },
      completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', label: 'Completed' },
      failed: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', label: 'Failed' },
    };
    return configs[status] || { bg: 'bg-zinc-100', text: 'text-zinc-800', dot: 'bg-zinc-500', label: status };
  };

  if (loading) {
    return (
      <div className="p-12 flex justify-center border-t border-zinc-100">
        <div className="inline-flex items-center justify-center gap-3 text-zinc-500">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-zinc-900"></div>
          <span className="text-[13px] font-medium">Loading history...</span>
        </div>
      </div>
    );
  }

  if (!merchantId) {
    return (
      <div className="p-12 flex justify-center border-t border-zinc-100">
        <p className="text-[14px] font-medium text-zinc-500">Please enter a merchant ID to view payout history.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[13px]">
        <thead>
          <tr className="bg-zinc-50/50 border-b border-zinc-100">
            <th className="px-5 py-2.5 font-medium text-zinc-500 w-[100px]">ID</th>
            <th className="px-5 py-2.5 font-medium text-zinc-500">Amount</th>
            <th className="px-5 py-2.5 font-medium text-zinc-500">Bank Account</th>
            <th className="px-5 py-2.5 font-medium text-zinc-500">Status</th>
            <th className="px-5 py-2.5 font-medium text-zinc-500 text-center">Retries</th>
            <th className="px-5 py-2.5 font-medium text-zinc-500 text-right">Date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {payouts.map((p) => {
            const statusConfig = getStatusConfig(p.status);
            return (
              <tr key={p.id} className="hover:bg-zinc-50/50 transition-colors group">
                <td className="px-5 py-3.5 align-middle">
                  <span className="text-[12px] font-mono text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200/50 block w-max">
                    {p.id.slice(0, 8)}
                  </span>
                </td>
                <td className="px-5 py-3.5 align-middle">
                  <span className="font-semibold text-zinc-900 tracking-tight">
                    {formatMoney(p.amount_paise)}
                  </span>
                </td>
                <td className="px-5 py-3.5 align-middle text-zinc-600 font-medium">{p.bank_account_id}</td>
                <td className="px-5 py-3.5 align-middle">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[12px] font-medium ${statusConfig.bg} ${statusConfig.text}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${statusConfig.dot}`}></span>
                    {statusConfig.label}
                  </span>
                </td>
                <td className="px-5 py-3.5 align-middle text-center">
                  {p.retry_count > 0 ? (
                    <span className="inline-flex items-center justify-center w-5 h-5 bg-zinc-100 text-zinc-700 rounded text-[11px] font-bold border border-zinc-200">
                      {p.retry_count}
                    </span>
                  ) : (
                    <span className="text-zinc-300">—</span>
                  )}
                </td>
                <td className="px-5 py-3.5 align-middle text-zinc-500 tabular-nums text-right">
                  {new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  <span className="text-zinc-400 ml-1.5">
                    {new Date(p.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </td>
              </tr>
            );
          })}
          {payouts.length === 0 && (
            <tr>
              <td colSpan="6" className="px-5 py-16 text-center">
                <div className="flex flex-col items-center justify-center gap-2">
                  <div className="w-10 h-10 bg-zinc-100 rounded-full flex items-center justify-center mb-1">
                    <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                      <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
                      <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
                      <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
                    </svg>
                  </div>
                  <p className="text-[13px] text-zinc-600 font-medium">No payouts initiated</p>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default PayoutTable;
