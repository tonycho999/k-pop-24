import { createClient } from '@supabase/supabase-js';
import KeywordTicker from '@/components/KeywordTicker';
import Header from '@/components/Header';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabase = createClient(supabaseUrl, supabaseKey);

export const revalidate = 0;

export default async function Home() {
  console.log("K-Pop 24 접속..."); 
  
  let reports = [];
  let hotKeywords = ['BTS', 'NewJeans', 'Blackpink', 'Stray Kids', 'IU']; 

  try {
    const { data, error } = await supabase
      .from('hourly_reports')
      .select('*')
      .order('created_at', { ascending: false });
      
    if (!error && data) {
      reports = data;
      const allKeywords = data.flatMap((item: any) => item.keywords || []);
      if (allKeywords.length > 0) {
         hotKeywords = [...new Set([...allKeywords, ...hotKeywords])].slice(0, 10);
      }
    }
  } catch (e) {
    console.error("데이터 로딩 실패:", e);
  }

  return (
    <main className="min-h-screen bg-black text-white p-6 md:p-12">
      <div className="max-w-5xl mx-auto">
        <Header />
        <div className="text-center mb-10">
          <h1 className="text-5xl md:text-6xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-pink-500 to-purple-600 mb-4 animate-pulse">
            Today's Issue 🚀
          </h1>
          <p className="text-gray-400 text-lg">Global K-Pop News Curator</p>
        </div>
        <div className="relative max-w-2xl mx-auto mb-4">
          <input type="text" placeholder="Search Past News..." className="w-full bg-gray-900 border border-gray-700 text-white px-6 py-4 rounded-full focus:outline-none focus:border-pink-500 transition-all shadow-lg text-lg"/>
          <button className="absolute right-3 top-2.5 bg-pink-600 hover:bg-pink-500 text-white px-6 py-2 rounded-full font-bold transition-colors">Search</button>
        </div>
        <KeywordTicker keywords={hotKeywords} />
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {reports.map((item: any) => (
            <div key={item.id} className="group relative bg-gray-900 rounded-3xl overflow-hidden border border-gray-800 hover:border-pink-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-pink-900/20 hover:-translate-y-1">
              <div className="p-6 pb-2">
                <div className="flex justify-between items-start mb-2">
                  <h2 className="text-3xl font-bold text-white group-hover:text-pink-400 transition-colors">{item.artist_name}</h2>
                  <span className="bg-gray-800 text-gray-400 text-xs px-2 py-1 rounded border border-gray-700">{new Date(item.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                </div>
              </div>
              <div className="px-6 py-2">
                <div className="text-gray-300 text-sm leading-relaxed line-clamp-4 group-hover:line-clamp-none transition-all" dangerouslySetInnerHTML={{ __html: item.summary_text }} />
              </div>
              <div className="p-6 pt-4 mt-auto">
                <button className="w-full bg-gradient-to-r from-gray-800 to-gray-900 hover:from-pink-900 hover:to-purple-900 text-white py-3 rounded-xl font-bold text-sm transition-all flex justify-center items-center gap-2 border border-gray-700 group-hover:border-pink-500">🔒 Unlock Full Report</button>
              </div>
            </div>
          ))}
          {reports.length === 0 && (
            <div className="col-span-full text-center py-20">
              <p className="text-2xl text-gray-500 font-light">Loading News...</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
