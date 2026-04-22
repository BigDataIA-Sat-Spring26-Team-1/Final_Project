'use client';

import { useEffect, useState } from 'react';
import { Save, Loader2 } from 'lucide-react';
import { getPersona, updateUserProfile } from '@/lib/api';
import { UserSwitcher } from '@/components/UserSwitcher';
import type { StoredPersona } from '@/lib/api';

export default function UserProfilePage() {
  const [userId, setUserId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('selectedUserId') || '';
    }
    return '';
  });

  const [persona, setPersona] = useState<StoredPersona | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form fields
  const [fullName, setFullName] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [seniority, setSeniority] = useState('');
  const [bioSummary, setBioSummary] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');

  useEffect(() => {
    if (userId) {
      sessionStorage.setItem('selectedUserId', userId);
      fetchPersona();
    }
  }, [userId]);

  const fetchPersona = async () => {
    if (!userId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await getPersona(userId);
      setPersona(data);
      setFullName('');
      setJobTitle(data.job_title || '');
      setSeniority(data.seniority || '');
      setBioSummary(data.bio_summary || '');
      setLinkedinUrl('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load persona');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!userId) {
      setError('Please select a user first');
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await updateUserProfile(userId, fullName || undefined, jobTitle, seniority, bioSummary, linkedinUrl);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      await fetchPersona();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUserSelect = (newUserId: string) => {
    setUserId(newUserId);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm p-8">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-3xl font-bold text-slate-900">User Profile</h1>
            <UserSwitcher currentUserId={userId} onSelect={handleUserSelect} />
          </div>

          {!userId ? (
            <div className="p-6 bg-amber-50 rounded-lg border border-amber-200">
              <p className="text-amber-900">Please select a user from the dropdown to edit their profile.</p>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center gap-3 py-12">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <span className="text-slate-600">Loading profile...</span>
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
                  <p className="text-green-900">Profile updated successfully!</p>
                </div>
              )}

              <div className="space-y-6">
                {/* Full Name */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    placeholder="Enter full name"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* Job Title */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Job Title
                  </label>
                  <input
                    type="text"
                    value={jobTitle}
                    onChange={e => setJobTitle(e.target.value)}
                    placeholder="e.g., Senior Machine Learning Engineer"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* Seniority */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Seniority Level
                  </label>
                  <select
                    value={seniority}
                    onChange={e => setSeniority(e.target.value)}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none bg-white"
                  >
                    <option value="">Select seniority level</option>
                    <option value="entry">Entry Level</option>
                    <option value="mid">Mid Level</option>
                    <option value="senior">Senior</option>
                    <option value="lead">Lead</option>
                    <option value="executive">Executive</option>
                  </select>
                </div>

                {/* Bio Summary */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Professional Bio
                  </label>
                  <textarea
                    value={bioSummary}
                    onChange={e => setBioSummary(e.target.value)}
                    placeholder="Brief professional background (2-3 sentences)"
                    rows={4}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* LinkedIn URL */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    LinkedIn URL
                  </label>
                  <input
                    type="url"
                    value={linkedinUrl}
                    onChange={e => setLinkedinUrl(e.target.value)}
                    placeholder="https://linkedin.com/in/..."
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                </div>

                {/* Current Weights Display */}
                {persona && (
                  <div className="pt-6 border-t border-slate-200">
                    <h3 className="text-sm font-semibold text-slate-900 mb-4">Interest Categories</h3>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(persona.explicit_category_weights)
                        .filter(([, weight]) => weight > 0)
                        .map(([category, weight]) => (
                          <div key={category} className="flex items-center justify-between">
                            <span className="text-sm text-slate-700 capitalize">
                              {category.replace(/_/g, ' ')}
                            </span>
                            <span className="text-sm font-medium text-blue-600">{(weight * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

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
                      Save Profile
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
