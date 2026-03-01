import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar.tsx';
import DotGrid from '../effects/DotGrid.tsx';

export default function DashboardLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <DotGrid />
      <Sidebar />
      <main className="flex-1 overflow-y-auto relative" style={{ zIndex: 1 }}>
        <div className="p-6 max-w-[1600px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
