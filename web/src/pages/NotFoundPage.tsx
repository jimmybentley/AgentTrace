import { Link } from 'react-router-dom';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-24 h-24 mb-6 rounded-full bg-slate-800 flex items-center justify-center">
        <svg
          className="w-12 h-12 text-slate-500"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h1 className="text-4xl font-bold text-slate-200 mb-2">404</h1>
      <p className="text-xl text-slate-400 mb-6">Page Not Found</p>
      <Link
        to="/traces"
        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
      >
        Go to Traces
      </Link>
    </div>
  );
};
