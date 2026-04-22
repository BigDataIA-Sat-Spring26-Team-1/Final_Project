'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
import { listUsers } from '@/lib/api';
import type { UserListItem } from '@/lib/api';

interface UserSwitcherProps {
  currentUserId: string | null;
  onSelect: (userId: string) => void;
}

export function UserSwitcher({ currentUserId, onSelect }: UserSwitcherProps) {
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentUser = users.find(u => u.id === currentUserId);

  useEffect(() => {
    const fetchUsers = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await listUsers(100);
        setUsers(res.results);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load users');
      } finally {
        setIsLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handleSelect = (userId: string) => {
    onSelect(userId);
    setIsOpen(false);
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition"
      >
        <span className="text-sm font-medium text-slate-700">
          {currentUser?.full_name || currentUser?.email || 'Select User'}
        </span>
        <ChevronDown className="w-4 h-4 text-slate-500" />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-slate-200 rounded-lg shadow-lg z-50">
          {isLoading ? (
            <div className="p-4 flex items-center justify-center gap-2 text-slate-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading users...</span>
            </div>
          ) : error ? (
            <div className="p-4 text-sm text-red-600">{error}</div>
          ) : users.length === 0 ? (
            <div className="p-4 text-sm text-slate-500">No users found</div>
          ) : (
            <ul className="max-h-64 overflow-y-auto">
              {users.map(user => (
                <li key={user.id}>
                  <button
                    onClick={() => handleSelect(user.id)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-50 transition ${
                      user.id === currentUserId ? 'bg-slate-100' : ''
                    }`}
                  >
                    <div className="font-medium text-slate-900">
                      {user.full_name || 'Unnamed'}
                    </div>
                    <div className="text-xs text-slate-500">{user.email}</div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
