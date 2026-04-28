import React, { useState } from 'react';
import { createPayout } from '../api';

function PayoutForm({ merchantId, onPayoutCreated }) {
  const [amount, setAmount] = useState('');
  const [bankAccount, setBankAccount] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!amount || !bankAccount || !merchantId) return;

    setLoading(true);
    setResult(null);

    try {
      const amountPaise = Math.round(parseFloat(amount) * 100);
      const idempotencyKey = crypto.randomUUID();

      const response = await createPayout(
        {
          amount_paise: amountPaise,
          bank_account_id: bankAccount,
        },
        idempotencyKey
      );

      setResult({
        success: true,
        message: 'Payout created successfully!',
        id: response.data.id,
        status: response.data.status,
      });
      setAmount('');
      setBankAccount('');
      if (onPayoutCreated) onPayoutCreated();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setResult({
        success: false,
        message: detail,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <label className="block text-[13px] font-medium text-zinc-700">Amount (INR)</label>
        <div className="relative border border-zinc-200 rounded-md shadow-sm bg-white hover:border-zinc-300 focus-within:ring-2 focus-within:ring-zinc-900 focus-within:border-zinc-900 transition-all overflow-hidden flex items-center">
          <span className="pl-3 text-zinc-500 font-medium text-[14px]">?</span>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            className="w-full pl-2 pr-3 py-2 text-zinc-900 text-[14px] font-medium outline-none placeholder:text-zinc-400 placeholder:font-normal bg-transparent"
            required
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="block text-[13px] font-medium text-zinc-700">Bank Account ID</label>
        <input
          type="text"
          value={bankAccount}
          onChange={(e) => setBankAccount(e.target.value)}
          placeholder="e.g. HDFC0001234"
          className="w-full px-3 py-2 bg-white border border-zinc-200 rounded-md text-zinc-900 text-[14px] font-medium shadow-sm hover:border-zinc-300 focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none transition placeholder:text-zinc-400 placeholder:font-normal"
          required
        />
      </div>

      <button
        type="submit"
        disabled={loading || !merchantId}
        className={"w-full mt-2 py-2 px-4 rounded-md text-[13px] font-medium text-white shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-zinc-900 " + (loading || !merchantId ? "bg-zinc-300 cursor-not-allowed" : "bg-zinc-900 hover:bg-zinc-800")}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg>
            Processing...
          </span>
        ) : 'Request Payout'}
      </button>

      {result && (
        <div className={"p-3 rounded-md text-[13px] font-medium " + (result.success ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700")}>
          <div className="flex items-start gap-2 text-left">
            {result.success ? (
              <svg className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M20 6L9 17l-5-5"/></svg>
            ) : (
              <svg className="w-4 h-4 text-red-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            )}
            <div>
              <p>{result.message}</p>
              {result.id && <p className="text-[11px] mt-0.5 text-emerald-600/70">ID: {result.id}</p>}
            </div>
          </div>
        </div>
      )}
    </form>
  );
}

export default PayoutForm;
