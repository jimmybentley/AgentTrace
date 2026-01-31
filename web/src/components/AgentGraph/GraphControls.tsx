interface GraphControlsProps {
  onZoomReset?: () => void;
  onLayoutChange?: () => void;
}

export const GraphControls: React.FC<GraphControlsProps> = ({
  onZoomReset,
  onLayoutChange,
}) => {
  return (
    <div className="absolute top-4 left-4 flex gap-2">
      {onZoomReset && (
        <button
          onClick={onZoomReset}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition-colors"
          title="Reset zoom"
        >
          Reset Zoom
        </button>
      )}
      {onLayoutChange && (
        <button
          onClick={onLayoutChange}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition-colors"
          title="Re-layout graph"
        >
          Re-layout
        </button>
      )}
    </div>
  );
};
