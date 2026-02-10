import { createClient } from '@supabase/supabase-js';

// 1. 여기서 바로 Supabase 연결 (가장 확실한 방법)
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabase = createClient(supabaseUrl, supabaseKey);

// 2. 캐시 방지 (항상 최신 뉴스)
export const revalidate = 0;

export default async function Home() {
  console.log("Supabase 연결 시도 중..."); 
  
  // 3. 데이터 가져오기
  let reports = [];
  try {
    const { data, error } = await supabase
      .table('hourly_reports')
      .select('*')
      .order('id', { ascending: false });
      
    if (error) throw error;
    reports = data || [];
  } catch (e) {
    console.error("데이터 가져오기 실패:", e);
  }

  return (
    <main className="min-h-screen bg-black text-white p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-center mb-10 text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-500">
          K-Pulse 24 🚀
        </h1>

        <div className="grid gap-6 md:grid-cols-2">
          {reports.map((item: any) => (
            <div key={item.id} className="border border-gray-800 bg-gray-900 p-6 rounded-2xl shadow-xl hover:border-pink-500 transition-colors">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-white">{item.artist_name}</h2>
                <span className="text-sm text-gray-500">
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </div>
              
              <div className="text-gray-300 mb-6 leading-relaxed" dangerouslySetInnerHTML={{ __html: item.summary_text }} />
              
              <div className="flex flex-wrap gap-2">
                {item.keywords?.map((k: string, i: number) => (
                  <span key={i} className="px-3 py-1 text-xs font-medium bg-gray-800 rounded-full text-pink-300 border border-gray-700">
                    #{k}
                  </span>
                ))}
              </div>
            </div>
          ))}

          {reports.length === 0 && (
            <div className="col-span-2 text-center py-20 text-gray-500">
              <p>뉴스를 불러오는 중입니다...</p>
              <p className="text-xs mt-2 text-gray-600">(혹은 데이터가 아직 없습니다)</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}