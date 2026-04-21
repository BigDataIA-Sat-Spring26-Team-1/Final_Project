'use client';

import { useEffect, useState } from 'react';
import { Calendar, Loader2, FileText } from 'lucide-react';
import { getBriefArchive } from '@/lib/api';
import { CompanySwitcher } from '@/components/CompanySwitcher';
import type { BriefArchiveItem } from '@/lib/api';

export default function BriefsPage() {
  const [companyId, setCompanyId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('selectedCompanyId') || '';
    }
    return '';
  });

  const [selectedDate, setSelectedDate] = useState<string>('');
  const [briefs, setBriefs] = useState<BriefArchiveItem[]>([]);
  const [selectedBrief, setSelectedBrief] = useState<BriefArchiveItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (companyId) {
      sessionStorage.setItem('selectedCompanyId', companyId);
      fetchBriefs();
    }
  }, [companyId, selectedDate]);

  const fetchBriefs = async () => {
    if (!companyId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await getBriefArchive(companyId, selectedDate || undefined, 30);
      setBriefs(res.results);
      if (res.results.length > 0 && !selectedBrief) {
        setSelectedBrief(res.results[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load briefs');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompanySelect = (newCompanyId: string) => {
    setCompanyId(newCompanyId);
  };

  const today = new Date().toISOString().split('T')[0];

  // Status badge color mapping
  const getStatusColor = (urgency: string | null) => {
    switch (urgency) {
      case 'ACT_NOW':
        return 'bg-red-100 text-red-700';
      case 'HIDDEN_GEM':
        return 'bg-green-100 text-green-700';
      case 'MONITOR':
        return 'bg-yellow-100 text-yellow-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Strategic Briefs Archive</h1>
          <CompanySwitcher currentCompanyId={companyId} onSelect={handleCompanySelect} />
        </div>

        {!companyId ? (
          <div className="p-6 bg-amber-50 rounded-lg border border-amber-200">
            <p className="text-amber-900">Please select a company to view their strategic briefs.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Left sidebar — date filter */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Filter by Date
              </h2>

              <input
                type="date"
                value={selectedDate}
                onChange={e => setSelectedDate(e.target.value)}
                max={today}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none mb-4"
              />

              {selectedDate && (
                <button
                  onClick={() => setSelectedDate('')}
                  className="w-full px-4 py-2 text-sm font-medium text-slate-700 hover:text-slate-900 transition"
                >
                  Clear filter
                </button>
              )}

              <div className="mt-6 pt-6 border-t border-slate-200">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Recent Briefs</h3>
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2 py-4 text-slate-500">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                ) : briefs.length === 0 ? (
                  <p className="text-sm text-slate-500">No briefs found</p>
                ) : (
                  <ul className="space-y-2">
                    {briefs.map(brief => (
                      <li key={brief.id}>
                        <button
                          onClick={() => setSelectedBrief(brief)}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                            selectedBrief?.id === brief.id
                              ? 'bg-blue-100 text-blue-900'
                              : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          <div className="font-medium">
                            {brief.generated_at
                              ? new Date(brief.generated_at).toLocaleDateString()
                              : 'Date unknown'}
                          </div>
                          {brief.urgency_tier && (
                            <div className="text-xs text-slate-600">
                              Priority: <span className="capitalize">{brief.urgency_tier}</span>
                            </div>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Right content — brief preview */}
            <div className="lg:col-span-3 bg-white rounded-xl shadow-sm p-8">
              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
                  <p className="text-red-900">{error}</p>
                </div>
              )}

              {!selectedBrief ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                  <FileText className="w-12 h-12 mb-4" />
                  <p>Select a brief to view</p>
                </div>
              ) : (
                <>
                  <div className="mb-6 pb-6 border-b border-slate-200">
                    <h2 className="text-2xl font-bold text-slate-900 mb-3">
                      Strategic Brief —{' '}
                      {selectedBrief.generated_at
                        ? new Date(selectedBrief.generated_at).toLocaleDateString()
                        : 'Date unknown'}
                    </h2>
                    {selectedBrief.urgency_tier && (
                      <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(selectedBrief.urgency_tier)}`}>
                        {selectedBrief.urgency_tier.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>

                  {selectedBrief.brief_content ? (
                    <div className="prose prose-sm max-w-none bg-slate-50 p-6 rounded-lg whitespace-pre-wrap text-slate-700">
                      {selectedBrief.brief_content}
                    </div>
                  ) : (
                    <p className="text-slate-500 italic">No content available for this brief.</p>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
