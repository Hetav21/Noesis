import { Outlet } from 'react-router';

function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-4">
      <h1 className="text-4xl font-bold text-center mb-8 text-gray-900">Deep Research Agent</h1>
      <Outlet />
    </div>
  );
}

export default App;
