import { createBrowserRouter, useRouteError, isRouteErrorResponse, Link } from 'react-router';
import App from './App';
import { HomePage } from './pages/HomePage';
import { ResearchPage } from './pages/ResearchPage';

function ErrorBoundary() {
  const error = useRouteError();
  
  let errorMessage = 'An unexpected error occurred';
  let errorStatus = '';
  
  if (isRouteErrorResponse(error)) {
    errorStatus = `${error.status}`;
    errorMessage = error.status === 404 
      ? 'Page not found' 
      : error.statusText || errorMessage;
  } else if (error instanceof Error) {
    errorMessage = error.message;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center">
        {errorStatus && (
          <h1 className="text-6xl font-bold text-gray-300 mb-4">{errorStatus}</h1>
        )}
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Oops!</h2>
        <p className="text-gray-600 mb-6">{errorMessage}</p>
        <Link 
          to="/" 
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded"
        >
          Go Home
        </Link>
      </div>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    errorElement: <ErrorBoundary />,
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
