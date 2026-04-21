'use client';

import { useState } from 'react';
import { Plus, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import {
  createUser,
  createCompany,
  triggerAdminIngestion,
  type IngestionTriggerResponse,
} from '@/lib/api';

export function AdminManagementPanel() {
  const [activeTab, setActiveTab] = useState<'user' | 'company' | 'ingestion'>('user');

  // User creation state
  const [userEmail, setUserEmail] = useState('');
  const [userFullName, setUserFullName] = useState('');
  const [userLoading, setUserLoading] = useState(false);
  const [userError, setUserError] = useState<string | null>(null);
  const [userSuccess, setUserSuccess] = useState(false);

  // Company creation state
  const [companyName, setCompanyName] = useState('');
  const [companyDomain, setCompanyDomain] = useState('');
  const [companyIndustry, setCompanyIndustry] = useState('');
  const [companyLoading, setCompanyLoading] = useState(false);
  const [companyError, setCompanyError] = useState<string | null>(null);
  const [companySuccess, setCompanySuccess] = useState(false);

  // Ingestion state
  const [ingestionLoading, setIngestionLoading] = useState(false);
  const [ingestionError, setIngestionError] = useState<string | null>(null);
  const [ingestionSuccess, setIngestionSuccess] = useState<IngestionTriggerResponse | null>(null);

  const handleCreateUser = async () => {
    if (!userEmail) {
      setUserError('Email is required');
      return;
    }

    setUserLoading(true);
    setUserError(null);
    setUserSuccess(false);

    try {
      await createUser(userEmail, userFullName);
      setUserSuccess(true);
      setUserEmail('');
      setUserFullName('');
      setTimeout(() => setUserSuccess(false), 3000);
    } catch (err) {
      setUserError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setUserLoading(false);
    }
  };

  const handleCreateCompany = async () => {
    if (!companyName) {
      setCompanyError('Company name is required');
      return;
    }

    setCompanyLoading(true);
    setCompanyError(null);
    setCompanySuccess(false);

    try {
      await createCompany(companyName, companyDomain, companyIndustry);
      setCompanySuccess(true);
      setCompanyName('');
      setCompanyDomain('');
      setCompanyIndustry('');
      setTimeout(() => setCompanySuccess(false), 3000);
    } catch (err) {
      setCompanyError(err instanceof Error ? err.message : 'Failed to create company');
    } finally {
      setCompanyLoading(false);
    }
  };

  const handleTriggerIngestion = async () => {
    setIngestionLoading(true);
    setIngestionError(null);
    setIngestionSuccess(null);

    try {
      const result = await triggerAdminIngestion();
      setIngestionSuccess(result);
    } catch (err) {
      setIngestionError(err instanceof Error ? err.message : 'Failed to trigger ingestion');
    } finally {
      setIngestionLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8">
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Admin Management</h2>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('user')}
          className={`px-4 py-2 font-medium transition border-b-2 ${
            activeTab === 'user'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          Create User
        </button>
        <button
          onClick={() => setActiveTab('company')}
          className={`px-4 py-2 font-medium transition border-b-2 ${
            activeTab === 'company'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          Create Company
        </button>
        <button
          onClick={() => setActiveTab('ingestion')}
          className={`px-4 py-2 font-medium transition border-b-2 ${
            activeTab === 'ingestion'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          Trigger Pipeline
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* Create User Tab */}
        {activeTab === 'user' && (
          <div className="space-y-4">
            {userError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <p className="text-red-900">{userError}</p>
              </div>
            )}

            {userSuccess && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
                <p className="text-green-900">User created successfully!</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Email</label>
              <input
                type="email"
                value={userEmail}
                onChange={e => setUserEmail(e.target.value)}
                placeholder="user@example.com"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Full Name (optional)</label>
              <input
                type="text"
                value={userFullName}
                onChange={e => setUserFullName(e.target.value)}
                placeholder="John Doe"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <button
              onClick={handleCreateUser}
              disabled={userLoading || !userEmail}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 rounded-lg transition"
            >
              {userLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create User
                </>
              )}
            </button>
          </div>
        )}

        {/* Create Company Tab */}
        {activeTab === 'company' && (
          <div className="space-y-4">
            {companyError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <p className="text-red-900">{companyError}</p>
              </div>
            )}

            {companySuccess && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
                <p className="text-green-900">Company created successfully!</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Company Name</label>
              <input
                type="text"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                placeholder="Acme Corporation"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Domain (optional)</label>
              <input
                type="url"
                value={companyDomain}
                onChange={e => setCompanyDomain(e.target.value)}
                placeholder="acme.com"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Industry (optional)</label>
              <input
                type="text"
                value={companyIndustry}
                onChange={e => setCompanyIndustry(e.target.value)}
                placeholder="Technology, Finance, Healthcare"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <button
              onClick={handleCreateCompany}
              disabled={companyLoading || !companyName}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 rounded-lg transition"
            >
              {companyLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create Company
                </>
              )}
            </button>
          </div>
        )}

        {/* Trigger Ingestion Tab */}
        {activeTab === 'ingestion' && (
          <div className="space-y-4">
            {ingestionError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <p className="text-red-900">{ingestionError}</p>
              </div>
            )}

            {ingestionSuccess && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-green-900 font-medium">Pipeline triggered successfully!</p>
                    <p className="text-green-800 text-sm mt-1">{ingestionSuccess.message}</p>
                    {ingestionSuccess.started_at && (
                      <p className="text-green-700 text-xs mt-1">
                        Started: {new Date(ingestionSuccess.started_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <p className="text-sm text-slate-700 mb-4">
                Trigger the RSS ingestion + URL-level deduplication pipeline. This will:
              </p>
              <ul className="list-disc list-inside space-y-2 text-sm text-slate-600 mb-4">
                <li>Fetch articles from RSS, ArXiv, and HackerNews</li>
                <li>Normalize URLs and detect duplicates</li>
                <li>Save new articles to the database</li>
                <li>Prepare data for the classification pipeline</li>
              </ul>
            </div>

            <button
              onClick={handleTriggerIngestion}
              disabled={ingestionLoading}
              className="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-400 text-white font-medium py-3 rounded-lg transition text-base"
            >
              {ingestionLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Pipeline running...
                </>
              ) : (
                <>
                  <Plus className="w-5 h-5" />
                  Trigger Force Sync
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
