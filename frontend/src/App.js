import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import PayoutForm from './components/PayoutForm';
import PayoutTable from './components/PayoutTable';
import { setMerchantId } from './api';

const MERCHANTS = [
  { id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479', name: 'Rahul Designs', email: 'rahul@designs.in', balance: '₹50,000' },
  { id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', name: 'Priya Tech Solutions', email: 'priya@tech.in', balance: '₹25,000' },
  { id: '5a6b7c8d-9e0f-1234-5678-9abcdef01234', name: 'Amit Studio', email: 'amit@studio.in', balance: '₹75,000' },
];

function App() {
  const [merchantId, setMerchantIdLocal] = useState(
    () => process.env.REACT_APP_MERCHANT_ID || ''
  );
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleMerchantChange = (e) => {
    const id = e.target.value;
    setMerchantIdLocal(id);
    setMerchantId(id);
  };

  const handlePayoutCreated = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const selectedMerchant = MERCHANTS.find(m => m.id === merchantId);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="bg-white shadow-sm rounded-lg p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl font-bold text-gray-900">Playto Payout Engine</h1>
            <div className="flex flex-col gap-1">
              <select
                value={merchantId}
                onChange={handleMerchantChange}
                className="px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none bg-white min-w-[280px]"
              >
                <option value="">-- Select a Merchant --</option>
                {MERCHANTS.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.balance})
                  </option>
                ))}
              </select>
              {selectedMerchant && (
                <p className="text-xs text-emerald-600 ml-1">{selectedMerchant.email}</p>
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
