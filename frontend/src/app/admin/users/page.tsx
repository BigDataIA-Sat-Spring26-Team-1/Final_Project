import { 
  Users, 
  Search, 
  Filter, 
  ChevronRight,
  MoreVertical,
  Mail
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { cn } from '@/lib/utils';

const MOCK_USERS = [
  { id: 1, name: 'Aakash', email: 'aakash@example.com', persona: 'Tech Strategist', status: 'ACTIVE', newsletters: 12 },
  { id: 2, name: 'Abhinav', email: 'abhinav@example.com', persona: 'Data Engineer', status: 'ACTIVE', newsletters: 8 },
  { id: 3, name: 'Rahul', email: 'rahul@example.com', persona: 'B2B Analyst', status: 'INACTIVE', newsletters: 15 },
];

export default function AdminUsersPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">User Management</h1>
            <p className="text-dim text-lg">Inspect personas, data streams, and distribution history for all individuals.</p>
          </div>
          <div className="flex items-center gap-3">
             <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5">
                <Search className="w-4 h-4 text-dim mr-2" />
                <input type="text" placeholder="Search users..." className="bg-transparent border-none outline-none text-sm w-48" />
             </div>
             <button className="p-2.5 glass rounded-xl border border-white/5 hover:bg-white/5 transition-all">
                <Filter className="w-5 h-5 text-dim" />
             </button>
          </div>
        </header>

        <div className="glass rounded-3xl border border-white/5 overflow-hidden">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-white/5 text-left border-bottom border-white/5">
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim">User</th>
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim">Persona Alignment</th>
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim text-center">Newsletters</th>
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim">Status</th>
                <th className="px-6 py-4 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {MOCK_USERS.map((user) => (
                <tr key={user.id} className="hover:bg-white/[0.02] transition-colors group cursor-pointer">
                  <td className="px-6 py-6 font-medium">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-secondary/20 flex items-center justify-center text-secondary font-bold text-xs">
                        {user.name.charAt(0)}
                      </div>
                      <div>
                        <p className="font-bold text-white leading-none mb-1">{user.name}</p>
                        <p className="text-xs text-dim">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-6">
                    <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest border border-primary/20">
                      {user.persona}
                    </span>
                  </td>
                  <td className="px-6 py-6 text-center font-bold text-white">
                    {user.newsletters}
                  </td>
                  <td className="px-6 py-6">
                    <div className="flex items-center gap-2">
                       <div className={cn("w-2 h-2 rounded-full", user.status === 'ACTIVE' ? "bg-emerald-500" : "bg-zinc-500")} />
                       <span className="text-xs font-bold text-dim">{user.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-6 text-right">
                    <div className="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-2 hover:bg-white/5 rounded-lg text-dim hover:text-white"><Mail className="w-4 h-4" /></button>
                      <button className="p-2 hover:bg-white/5 rounded-lg text-dim hover:text-white"><ChevronRight className="w-4 h-4" /></button>
                      <button className="p-2 hover:bg-white/5 rounded-lg text-dim hover:text-white"><MoreVertical className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageWrapper>
  );
}
