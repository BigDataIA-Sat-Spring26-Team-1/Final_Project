'use client';

import { useEffect, useState } from 'react';
import { Save, Loader2 } from 'lucide-react';
import { updateCompanyProfile } from '@/lib/api';
import { CompanySwitcher } from '@/components/CompanySwitcher';

export default function CompanyProfilePage() {
  const [companyId, setCompanyId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('selectedCompanyId') || '';
    }
    return '';
  });

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form fields
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [industry, setIndustry] = useState('');
  const [description, setDescription] = useState('');
  const [companySize, setCompanySize] = useState('');

  useEffect(() => {
    if (companyId) {
      sessionStorage.setItem('selectedCompanyId', companyId);
      // TODO: In a future update, fetch company details from GET /api/v1/admin/companies/{id}
      // For now, only allow editing
    }
  }, [companyId]);

  const handleSave = async () => {
    if (!companyId) {
      setError('Please select a company first');
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await updateCompanyProfile(companyId, name, domain, industry, description, companySize);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save company profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCompanySelect = (newCompanyId: string) => {
    setCompanyId(newCompanyId);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm p-8">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-3xl font-bold text-slate-900">Company Profile</h1>
            <CompanySwitcher currentCompanyId={companyId} onSelect={handleCompanySelect} />
          </div>

          {!companyId ? (
            <div className="p-6 bg-amber-50 rounded-lg border border-amber-200">
              <p className="text-amber-900">Please select a company from the dropdown to edit their profile.</p>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-900">{error}</p>
                </div>
              )}

              {success && (
                <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-green-900">Company profile updated successfully!</p>
                </div>
              )}

              <div className="space-y-6">
                {/* Company Name */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Company Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="e.g., Acme Corporation"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* Domain */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Website Domain
                  </label>
                  <input
                    type="url"
                    value={domain}
                    onChange={e => setDomain(e.target.value)}
                    placeholder="e.g., acme.com"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* Industry */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Industry
                  </label>
                  <input
                    type="text"
                    value={industry}
                    onChange={e => setIndustry(e.target.value)}
                    placeholder="e.g., Technology, Finance, Healthcare"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* Company Size */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Company Size
                  </label>
                  <select
                    value={companySize}
                    onChange={e => setCompanySize(e.target.value)}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none bg-white"
                  >
                    <option value="">Select company size</option>
                    <option value="EARLY_STAGE">Early Stage (1-50 employees)</option>
                    <option value="GROWTH">Growth Stage (51-500 employees)</option>
                    <option value="MID_MARKET">Mid Market (501-5000 employees)</option>
                    <option value="ENTERPRISE">Enterprise (5000+ employees)</option>
                  </select>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Company Description
                  </label>
                  <textarea
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder="Brief description of the company and what they do"
                    rows={4}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* Save Button */}
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-3 rounded-lg transition"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-5 h-5" />
                      Save Company Profile
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
