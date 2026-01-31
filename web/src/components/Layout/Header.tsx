import { Link } from 'react-router-dom';

export const Header: React.FC = () => {
  return (
    <header className="bg-slate-800 border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-8 h-8">
              <svg viewBox="0 0 100 100" className="w-full h-full">
                <circle cx="50" cy="50" r="45" fill="#3b82f6" />
                <path
                  d="M30 40 L50 25 L70 40 M50 25 L50 75 M30 60 L50 75 L70 60"
                  stroke="white"
                  strokeWidth="4"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100">AgentTrace</h1>
              <p className="text-xs text-slate-400">Multi-Agent Observability</p>
            </div>
          </Link>

          <nav className="flex items-center gap-6">
            <Link
              to="/traces"
              className="text-sm font-medium text-slate-300 hover:text-slate-100 transition-colors"
            >
              Traces
            </Link>
            <a
              href="https://github.com/jimmybentley/AgentTrace"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-slate-300 hover:text-slate-100 transition-colors"
            >
              GitHub
            </a>
          </nav>
        </div>
      </div>
    </header>
  );
};
