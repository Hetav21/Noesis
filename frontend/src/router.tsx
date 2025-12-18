import { createBrowserRouter } from 'react-router';
import App from './App';
import { HomePage } from './pages/HomePage';
import { ResearchPage } from './pages/ResearchPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'research/:jobId',
        element: <ResearchPage />,
      },
    ],
  },
]);
