'use client';

import { useEffect, useState } from 'react';
import { Calendar, Loader2, BookOpen } from 'lucide-react';
import { getNewsletterArchive } from '@/lib/api';
import { UserSwitcher } from '@/components/UserSwitcher';
import type { NewsletterArchiveItem } from '@/lib/api';

export default function NewslettersPage() {
  const [userId, setUserId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('selectedUserId') || '';
    }
    return '';
  });

  const [selectedDate, setSelectedDate] = useState<string>('');
  const [newsletters, setNewsletters] = useState<NewsletterArchiveItem[]>([]);
  const [selectedNewsletter, setSelectedNewsletter] = useState<NewsletterArchiveItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (userId) {
      sessionStorage.setItem('selectedUserId', userId);
      fetchNewsletters();
    }
  }, [userId, selectedDate]);

  const fetchNewsletters = async () => {
    if (!userId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await getNewsletterArchive(userId, selectedDate || undefined, 30);
      setNewsletters(res.results);
      if (res.results.length > 0 && !selectedNewsletter) {
        setSelectedNewsletter(res.results[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load newsletters');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUserSelect = (newUserId: string) => {
    setUserId(newUserId);
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Newsletter Archive</h1>
          <UserSwitcher currentUserId={userId} onSelect={handleUserSelect} />
        </div>

        {!userId ? (
          <div className="p-6 bg-amber-50 rounded-lg border border-amber-200">
            <p className="text-amber-900">Please select a user to view their newsletters.</p>
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
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Recent Newsletters</h3>
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2 py-4 text-slate-500">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                ) : newsletters.length === 0 ? (
                  <p className="text-sm text-slate-500">No newsletters found</p>
                ) : (
                  <ul className="space-y-2">
                    {newsletters.map(nl => (
                      <li key={nl.id}>
                        <button
                          onClick={() => setSelectedNewsletter(nl)}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                            selectedNewsletter?.id === nl.id
                              ? 'bg-blue-100 text-blue-900'
                              : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          <div className="font-medium">
                            {new Date(nl.edition_date).toLocaleDateString()}
                          </div>
                          <div className="text-xs text-slate-600">
                            Status: <span className="capitalize">{nl.status}</span>
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Right content — newsletter preview */}
            <div className="lg:col-span-3 bg-white rounded-xl shadow-sm p-8">
              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
                  <p className="text-red-900">{error}</p>
                </div>
              )}

              {!selectedNewsletter ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                  <BookOpen className="w-12 h-12 mb-4" />
                  <p>Select a newsletter to view</p>
                </div>
              ) : (
                <>
                  <div className="mb-6 pb-6 border-b border-slate-200">
                    <h2 className="text-2xl font-bold text-slate-900 mb-2">
                      Newsletter — {new Date(selectedNewsletter.edition_date).toLocaleDateString()}
                    </h2>
                    <div className="flex items-center gap-4 text-sm text-slate-600">
                      <span className="capitalize px-2 py-1 bg-blue-100 text-blue-700 rounded">
                        {selectedNewsletter.status}
                      </span>
                      {selectedNewsletter.generated_at && (
                        <span>Generated: {new Date(selectedNewsletter.generated_at).toLocaleString()}</span>
                      )}
                      {selectedNewsletter.execution_path_taken && (
                        <span className="text-xs">Path: {selectedNewsletter.execution_path_taken}</span>
                      )}
                    </div>
                  </div>

                  {selectedNewsletter.final_content ? (
                    <div
                      className="prose prose-sm max-w-none bg-slate-50 p-6 rounded-lg"
                      dangerouslySetInnerHTML={{ __html: selectedNewsletter.final_content }}
                    />
                  ) : selectedNewsletter.draft_content ? (
                    <div className="bg-slate-50 p-6 rounded-lg whitespace-pre-wrap text-slate-700">
                      {selectedNewsletter.draft_content}
                    </div>
                  ) : (
                    <p className="text-slate-500 italic">No content available for this newsletter.</p>
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
