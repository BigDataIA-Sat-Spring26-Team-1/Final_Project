import { 
  Building2, 
  Search, 
  Filter, 
  ChevronRight,
  MoreVertical,
  Briefcase
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';

const MOCK_COMPANIES = [
  { id: 1, name: 'Cloud Infrastructure Corp', sector: 'Cloud Computing', status: 'ACTIVE', authority: 0.89 },
  { id: 2, name: 'Vector Secure', sector: 'Cybersecurity', status: 'ACTIVE', authority: 0.72 },
  { id: 3, name: 'AI Gen Systems', sector: 'Generative AI', status: 'PENDING', authority: 0.45 },
];

export default function AdminCompaniesPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Enterprise Portfolio</h1>
            <p className="text-dim text-lg">Manage corporate authority profiles and B2B content strategy settings.</p>
          </div>
          <div className="flex items-center gap-3">
             <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5">
                <Search className="w-4 h-4 text-dim mr-2" />
                <input type="text" placeholder="Search companies..." className="bg-transparent border-none outline-none text-sm w-48" />
             </div>
          </div>
        </header>

        <div className="glass rounded-3xl border border-white/5 overflow-hidden">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-white/5 text-left border-bottom border-white/5">
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim">Company</th>
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim">Active Sector</th>
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim text-center">Authority</th>
                <th className="px-6 py-4 text-xs font-black uppercase tracking-widest text-dim">Status</th>
                <th className="px-6 py-4 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {MOCK_COMPANIES.map((company) => (
                <tr key={company.id} className="hover:bg-white/[0.02] transition-colors group cursor-pointer">
                  <td className="px-6 py-6 font-medium">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-xs uppercase">
                        {company.name.charAt(0)}
                      </div>
                      <p className="font-bold text-white">{company.name}</p>
                    </div>
                  </td>
                  <td className="px-6 py-6">
                    <span className="px-3 py-1 rounded-full bg-secondary/10 text-secondary text-[10px] font-black uppercase tracking-widest border border-secondary/20">
                      {company.sector}
                    </span>
                  </td>
                  <td className="px-6 py-6 text-center">
                    <div className="flex flex-col items-center">
                       <span className="text-sm font-bold text-white">{company.authority}</span>
                       <div className="w-16 h-1 bg-white/5 rounded-full mt-1">
                          <div className="h-full bg-primary rounded-full" style={{ width: `${company.authority * 100}%` }} />
                       </div>
                    </div>
                  </td>
                  <td className="px-6 py-6">
                    <span className="text-xs font-bold text-dim">{company.status}</span>
                  </td>
                  <td className="px-6 py-6 text-right">
                    <div className="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
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
