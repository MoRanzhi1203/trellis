import { NavLink, Outlet } from 'react-router-dom'

const nav = [
  { to: '/', label: '首页', end: true },
  { to: '/dictionary', label: '词库' },
  { to: '/study', label: '学习与复习' },
  { to: '/graph', label: '知识图谱' },
  { to: '/imports', label: '导入与备份' },
]

export default function Layout() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          Trellis <span>词汇知识图谱</span>
        </div>
        <nav>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span>本地 SQLite</span>
          <span className="dot" />
          <span>127.0.0.1</span>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
