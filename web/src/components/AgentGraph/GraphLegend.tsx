import { roleColors } from '@/utils';

export const GraphLegend: React.FC = () => {
  const roles = [
    { name: 'Planner', color: roleColors.planner },
    { name: 'Executor', color: roleColors.executor },
    { name: 'Reviewer', color: roleColors.reviewer },
    { name: 'Coder', color: roleColors.coder },
    { name: 'Researcher', color: roleColors.researcher },
  ];

  return (
    <div className="absolute top-4 right-4 bg-slate-800 border border-slate-700 rounded-lg p-3">
      <h3 className="text-xs font-semibold text-slate-300 mb-2">Agent Roles</h3>
      <div className="space-y-1.5">
        {roles.map((role) => (
          <div key={role.name} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: role.color }}
            />
            <span className="text-xs text-slate-400">{role.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
