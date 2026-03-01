import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardLayout from './components/layout/DashboardLayout.tsx';
import LiveMonitor from './pages/LiveMonitor.tsx';
import CaseDetail from './pages/CaseDetail.tsx';
import SentinelIndex from './pages/SentinelIndex.tsx';
import Arena from './pages/Arena.tsx';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<LiveMonitor />} />
          <Route path="/case/:caseId" element={<CaseDetail />} />
          <Route path="/index" element={<SentinelIndex />} />
          <Route path="/arena" element={<Arena />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
