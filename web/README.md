# AgentTrace Web UI

React frontend for AgentTrace - Multi-Agent LLM Debugging & Observability Platform.

## Features

- **Trace List**: Paginated list of traces with filtering and search
- **Agent Graph**: D3.js force-directed graph visualization of agent communication
- **Span Timeline**: Gantt-style timeline showing span execution
- **Failure Analysis**: Display and filter failure annotations using MAST taxonomy
- **Span Details**: View detailed span information with JSON input/output

## Tech Stack

- React 18 + TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- React Query (TanStack Query) for data fetching
- D3.js for graph visualization
- React Router for navigation

## Development

Install dependencies:

```bash
npm install
```

Start development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Configuration

The API base URL can be configured via environment variable:

```bash
VITE_API_URL=http://localhost:8000/api npm run dev
```

By default, the app uses Vite's proxy to forward `/api` requests to `http://localhost:8000`.

## Build

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Project Structure

```
src/
├── api/              # API client and type definitions
├── hooks/            # React Query hooks
├── components/       # React components
│   ├── Layout/       # Header and layout components
│   ├── TraceList/    # Trace list and filters
│   ├── TraceDetail/  # Trace detail view
│   ├── AgentGraph/   # D3.js graph visualization
│   ├── SpanTimeline/ # Gantt-style timeline
│   ├── SpanDetail/   # Span detail view
│   ├── FailurePanel/ # Failure annotations
│   └── common/       # Reusable components
├── pages/            # Page components
├── utils/            # Utility functions
└── App.tsx           # Main app component
```
