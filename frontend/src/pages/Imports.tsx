import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

export default function Imports() {
  const [restoreFile, setRestoreFile] = useState('')

  const legacy = useMutation({ mutationFn: api.imports.legacy })
  const backup = useMutation({ mutationFn: api.imports.backup })
  const restore = useMutation({ mutationFn: (file: string) => api.imports.restore(file) })
  const books = useQuery({ queryKey: ['books'], queryFn: api.books.list })

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>导入与备份</h1>
          <p>旧数据迁移是幂等的：重复执行不会产生重复词条</p>
        </div>
      </div>

      <div className="panel">
        <h2>旧版数据迁移</h2>
        <p className="small muted">
          只读解析 data/words.js、词族网络图.html、词族词库_fin-volv.xlsx、词族知识库_fin-volv.md，写入 SQLite。
        </p>
        <button className="primary" disabled={legacy.isPending} onClick={() => legacy.mutate()}>
          {legacy.isPending ? '导入中…' : '运行迁移'}
        </button>
        {legacy.data && (
          <div className="banner ok" style={{ marginTop: 12 }}>
            <div>词条创建 {legacy.data.counts.lexemes_created ?? 0} 条，合并 {legacy.data.counts.lexemes_merged ?? 0} 条</div>
            <div>义项 {legacy.data.counts.senses ?? 0} 条，关系 {legacy.data.counts.edges ?? 0} 条（待审核 {legacy.data.counts.edges_pending ?? 0}）</div>
            {legacy.data.errors.length > 0 && <div className="banner err">{legacy.data.errors.join('；')}</div>}
          </div>
        )}
        {legacy.isError && <div className="banner err">{String(legacy.error)}</div>}
      </div>

      <div className="panel">
        <h2>备份与恢复</h2>
        <div className="toolbar">
          <button className="primary" disabled={backup.isPending} onClick={() => backup.mutate()}>
            创建备份
          </button>
          {backup.data && <span className="small muted">{backup.data.file}（{Math.round(backup.data.size / 1024)} KB）</span>}
        </div>
        <div className="toolbar">
          <input
            placeholder="备份文件名，例如 trellis-20261105-120000.db"
            value={restoreFile}
            onChange={(event) => setRestoreFile(event.target.value)}
            style={{ width: 360 }}
          />
          <button disabled={!restoreFile.trim() || restore.isPending} onClick={() => restore.mutate(restoreFile.trim())}>
            恢复
          </button>
        </div>
        {restore.data && <div className="banner ok">已恢复：{restore.data.ok ? '成功' : '失败'}</div>}
        {restore.isError && <div className="banner err">{String(restore.error)}</div>}
      </div>

      <div className="panel">
        <h2>词书</h2>
        {books.data?.map((book) => (
          <div key={book.id} className="small">
            <strong>{book.title}</strong> — {book.description}
          </div>
        ))}
      </div>
    </div>
  )
}
