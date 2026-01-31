import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import type { AgentNode, CommunicationEdge } from '@/api/types';
import { getRoleColor } from '@/utils';

interface AgentGraphProps {
  nodes: AgentNode[];
  edges: CommunicationEdge[];
  onNodeClick?: (node: AgentNode) => void;
  onEdgeClick?: (edge: CommunicationEdge) => void;
  highlightedAgent?: string;
  failedAgents?: string[];
}

type SimulationNode = AgentNode & d3.SimulationNodeDatum;
type SimulationLink = CommunicationEdge & d3.SimulationLinkDatum<SimulationNode>;

export const AgentGraph: React.FC<AgentGraphProps> = ({
  nodes,
  edges,
  onNodeClick,
  onEdgeClick,
  highlightedAgent,
  failedAgents = [],
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const handleResize = () => {
      if (svgRef.current) {
        const rect = svgRef.current.parentElement?.getBoundingClientRect();
        if (rect) {
          setDimensions({ width: rect.width, height: rect.height });
        }
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;

    // Create container with zoom
    const container = svg.append('g').attr('class', 'graph-container');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        container.attr('transform', event.transform.toString());
      });

    svg.call(zoom);

    // Convert nodes and edges to simulation format
    const simulationNodes: SimulationNode[] = nodes.map((node) => ({ ...node }));
    const simulationLinks: SimulationLink[] = edges.map((edge) => ({
      ...edge,
      source: edge.source,
      target: edge.target,
    }));

    // Create force simulation
    const simulation = d3
      .forceSimulation(simulationNodes)
      .force(
        'link',
        d3
          .forceLink<SimulationNode, SimulationLink>(simulationLinks)
          .id((d) => d.id)
          .distance(150)
      )
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(60));

    // Draw edges
    const edgeGroup = container.append('g').attr('class', 'edges');

    const edgeElements = edgeGroup
      .selectAll('g')
      .data(simulationLinks)
      .enter()
      .append('g')
      .attr('class', 'edge')
      .style('cursor', 'pointer')
      .on('click', (_event, d) => onEdgeClick?.(d as CommunicationEdge));

    // Edge lines with arrows
    edgeElements
      .append('line')
      .attr('stroke', '#94a3b8')
      .attr('stroke-width', (d) => Math.min(4, 1 + d.message_count / 2))
      .attr('marker-end', 'url(#arrowhead)');

    // Edge labels (message count)
    edgeElements
      .append('text')
      .attr('class', 'edge-label')
      .attr('text-anchor', 'middle')
      .attr('dy', -5)
      .attr('fill', '#64748b')
      .attr('font-size', '11px')
      .text((d) => (d.message_count > 1 ? `×${d.message_count}` : ''));

    // Draw nodes
    const nodeGroup = container.append('g').attr('class', 'nodes');

    const nodeElements = nodeGroup
      .selectAll('g')
      .data(simulationNodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .on('click', (_event, d) => onNodeClick?.(d as AgentNode))
      .call(
        d3
          .drag<SVGGElement, SimulationNode>()
          .on('start', dragStarted)
          .on('drag', dragged)
          .on('end', dragEnded)
      );

    // Node circles
    nodeElements
      .append('circle')
      .attr('r', (d) => 30 + Math.log(d.span_count + 1) * 5)
      .attr('fill', (d) => {
        if (failedAgents.includes(d.id)) return '#ef4444';
        if (d.id === highlightedAgent) return '#3b82f6';
        return getRoleColor(d.role);
      })
      .attr('stroke', '#1e293b')
      .attr('stroke-width', 2);

    // Node labels
    nodeElements
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 4)
      .attr('fill', 'white')
      .attr('font-weight', 'bold')
      .attr('font-size', '12px')
      .text((d) => d.name.slice(0, 12));

    // Role subtitle
    nodeElements
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 50)
      .attr('fill', '#64748b')
      .attr('font-size', '10px')
      .text((d) => d.role);

    // Arrow marker definition
    svg
      .append('defs')
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 35)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .append('path')
      .attr('d', 'M 0,-5 L 10,0 L 0,5')
      .attr('fill', '#94a3b8');

    // Update positions on tick
    simulation.on('tick', () => {
      edgeElements
        .select('line')
        .attr('x1', (d) => (d.source as SimulationNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimulationNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimulationNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimulationNode).y ?? 0);

      edgeElements
        .select('text')
        .attr('x', (d) => ((d.source as SimulationNode).x! + (d.target as SimulationNode).x!) / 2)
        .attr('y', (d) => ((d.source as SimulationNode).y! + (d.target as SimulationNode).y!) / 2);

      nodeElements.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    function dragStarted(event: d3.D3DragEvent<SVGGElement, SimulationNode, SimulationNode>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, SimulationNode, SimulationNode>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragEnded(event: d3.D3DragEvent<SVGGElement, SimulationNode, SimulationNode>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, dimensions, highlightedAgent, failedAgents, onNodeClick, onEdgeClick]);

  return (
    <div className="agent-graph-container w-full h-full bg-slate-900 rounded-lg">
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        className="border border-slate-700 rounded-lg"
      />
    </div>
  );
};
