import { useEffect, useRef, useId } from 'react';
import mermaid from 'mermaid';

let initialized = false;

function initMermaid() {
  if (initialized) return;
  initialized = true;
  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
      primaryColor: '#1a1a1a',
      primaryTextColor: '#ff8c00',
      primaryBorderColor: '#ff6b0088',
      lineColor: '#ff6b00aa',
      secondaryColor: '#161616',
      tertiaryColor: '#0a0a0a',
      fontFamily: 'Courier New, monospace',
      fontSize: '12px',
      nodeBorder: '#ff6b0088',
      mainBkg: '#161616',
      clusterBkg: '#111111',
      clusterBorder: '#ff6b0055',
      titleColor: '#ff8c00',
      edgeLabelBackground: '#0a0a0a',
      nodeTextColor: '#ff8c00',
    },
  });
}

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

export default function MermaidDiagram({ chart, className = '' }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const uniqueId = useId().replace(/:/g, '-');

  useEffect(() => {
    initMermaid();

    let cancelled = false;
    const el = containerRef.current;
    if (!el) return;

    const render = async () => {
      try {
        const { svg } = await mermaid.render(`mermaid${uniqueId}`, chart);
        if (!cancelled && el) {
          el.innerHTML = svg;
        }
      } catch {
        if (!cancelled && el) {
          el.innerHTML = `<pre style="color:#ff6b0066;font-size:11px;white-space:pre-wrap">${chart}</pre>`;
        }
      }
    };

    render();

    return () => {
      cancelled = true;
    };
  }, [chart, uniqueId]);

  return (
    <div
      ref={containerRef}
      className={`mermaid-container ${className}`}
    />
  );
}
