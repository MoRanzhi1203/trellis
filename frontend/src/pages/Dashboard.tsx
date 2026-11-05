import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../services/api'

export default function Dashboard() {
  const stats = useQuery({ queryKey: ['stats'], queryFn: api.stats })
  const history = useQuery({ queryKey: ['history'], queryFn: api.reviews.history })

  const data = stats.data
  return (
    <div>
      <div className="page-head">
        <div>
          <h1>今日</h1>
          <p>学习任务与复习进度全部来自本地数据库</p>
        </div>
        <Link to="/study">
          <button className="primary">开始复习</button>
        </Link>
      </div>

      {stats.isLoading && <div className="banner">加载中…</div>}
      {stats.isError && <div className="banner err">无法连接后端：{String(stats.error)}</div>}

      {data && (
        <>
          <div className="cards">
            <div className="card">
              <div className="label">词库总量</div>
              <div className="value">{data.total_lexemes}</div>
              <div className="hint">{data.total_cards} 张记忆卡</div>
            </div>
            <div className="card">
              <div className="label">今日待复习</div>
              <div className="value">{data.due_today}</div>
              <div className="hint">已复习 {data.reviewed_today} 次</div>
            </div>
            <div className="card">
              <div className="label">今日正确率</div>
              <div className="value">{Math.round(data.accuracy_today * 100)}%</div>
              <div className="hint">新学 {data.learned_today} 条</div>
            </div>
            <div className="card">
              <div className="label">连续学习</div>
              <div className="value">{data.streak_days} 天</div>
              <div className="hint">以复习记录计算</div>
            </div>
          </div>

          <div className="panel">
            <h2>薄弱词</h2>
            {data.weak_words.length === 0 ? (
              <div className="muted small">还没有「again」记录。</div>
            ) : (
              <table>
                <thead>
                  <tr><th>词</th><th>遗忘次数</th></tr>
                </thead>
                <tbody>
                  {data.weak_words.map((word) => (
                    <tr key={word.headword}>
                      <td className="mono">{word.headword}</td>
                      <td>{word.misses}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="panel">
            <h2>最近复习</h2>
            {history.data && history.data.length > 0 ? (
              <ul className="small">
                {(history.data as { id: number; card_type: string; result: string; reviewed_at: string }[])
                  .slice(0, 8)
                  .map((item) => (
                    <li key={item.id}>
                      {new Date(item.reviewed_at).toLocaleString()} · {item.card_type} · {item.result}
                    </li>
                  ))}
              </ul>
            ) : (
              <div className="muted small">还没有复习记录。</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
