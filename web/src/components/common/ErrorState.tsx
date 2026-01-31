interface ErrorStateProps {
  message?: string;
  retry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = 'An error occurred while loading data',
  retry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-16 h-16 mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-red-500"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-slate-200 mb-2">Error</h3>
      <p className="text-slate-400 mb-4 max-w-md">{message}</p>
      {retry && (
        <button
          onClick={retry}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
};
