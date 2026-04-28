import React, { useState, useCallback } from 'react';
import Dashboard from './components/Dashboard';
import PayoutForm from './components/PayoutForm';
import PayoutTable from './components/PayoutTable';
import { setMerchantId } from './api';

function isValidUUID(str) {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

function App() {
  const [merchantId, setMerchantIdLocal] = useState(
    () => process.env.REACT_APP_MERCHANT_ID || ''
  );
  const [inputValue, setInputValue] = useState(
    () => process.env.REACT_APP_MERCHANT_ID || ''
  );
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [idError, setIdError] = useState('');

  const debounceTimer = React.useRef(null);

  const applyMerchantId = useCallback((id) => {
    setMerchantIdLocal(id);
    setMerchantId(id);
    setRefreshTrigger((prev) => prev + 1);
  }, []);

  const handleMerchantIdChange = (e) => {
    const val = e.target.value;
    setInputValue(val);

    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    debounceTimer.current = setTimeout(() => {
      const trimmed = val.trim();
      if (!trimmed) {
        setIdError('');
        return;
      }
      if (!isValidUUID(trimmed)) {
        setIdError('Please enter a valid UUID format');
        return;
      }
      setIdError('');
      applyMerchantId(trimmed);
    }, 500);
  };

  const handlePayoutCreated = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="bg-white shadow-sm rounded-lg p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl font-bold text-gray-900">Playto Payout Engine</h1>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700 whitespace-nowrap">Merchant ID:</label>
                <input
                  type="text"
                  value={inputValue}
                  onChange={handleMerchantIdChange}
                  placeholder="Enter merchant UUID"
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none font-mono w-80"
                />
              </div>
              {idError && <p className="text-xs text-red-600 ml-20">{idError}</p>}
              {merchantId && !idError && (
                <p className="text-xs text-emerald-600 ml-20">Connected to merchant</p>
              )}
            </div>
          </div>
          <Dashboard key={`dash-${refreshTrigger}`} merchantId={merchantId} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <div className="bg-white shadow-sm rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Request Payout</h2>
              <PayoutForm merchantId={merchantId} onPayoutCreated={handlePayoutCreated} />
            </div>
          </div>
          <div className="lg:col-span-2">
            <div className="bg-white shadow-sm rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Payout History</h2>
              <PayoutTable key={`table-${refreshTrigger}`} merchantId={merchantId} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
