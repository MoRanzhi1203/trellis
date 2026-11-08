import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from '../components/Layout'
import Dashboard from '../pages/Dashboard'
import Dictionary from '../pages/Dictionary'
import Graph from '../pages/Graph'
import Imports from '../pages/Imports'
import Study from '../pages/Study'
import Test from '../pages/Test'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="dictionary" element={<Dictionary />} />
        <Route path="study" element={<Study />} />
        <Route path="test" element={<Test />} />
        <Route path="graph" element={<Graph />} />
        <Route path="imports" element={<Imports />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
