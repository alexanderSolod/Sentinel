import { useEffect, useRef } from 'react';
import createGlobe from 'cobe';

export default function Globe() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let phi = 0;
    let width = 0;

    const onResize = () => {
      if (canvasRef.current) {
        width = canvasRef.current.offsetWidth;
      }
    };
    window.addEventListener('resize', onResize);
    onResize();

    const globe = createGlobe(canvasRef.current!, {
      devicePixelRatio: 2,
      width: width * 2,
      height: width * 2,
      phi: 0,
      theta: 0.25,
      dark: 1,
      diffuse: 2,
      mapSamples: 24000,
      mapBrightness: 10,
      baseColor: [0.06, 0.04, 0],
      markerColor: [1, 0.55, 0],
      glowColor: [0.5, 0.2, 0],
      markers: [
        // Geopolitical hotspots
        { location: [38.9072, -77.0369], size: 0.06 },  // Washington DC
        { location: [51.5074, -0.1278], size: 0.05 },   // London
        { location: [35.6762, 139.6503], size: 0.05 },   // Tokyo
        { location: [55.7558, 37.6173], size: 0.04 },    // Moscow
        { location: [31.2304, 121.4737], size: 0.05 },   // Shanghai
        { location: [25.2048, 55.2708], size: 0.04 },    // Dubai
        { location: [48.8566, 2.3522], size: 0.04 },     // Paris
        { location: [1.3521, 103.8198], size: 0.04 },    // Singapore
        { location: [19.4326, -99.1332], size: 0.03 },   // Mexico City
        { location: [-33.8688, 151.2093], size: 0.03 },  // Sydney
        { location: [35.6892, 51.3890], size: 0.04 },    // Tehran
        { location: [41.0082, 28.9784], size: 0.03 },    // Istanbul
      ],
      onRender: (state) => {
        state.phi = phi;
        phi += 0.003;
        state.width = width * 2;
        state.height = width * 2;
      },
    });

    setTimeout(() => {
      if (canvasRef.current) {
        canvasRef.current.style.opacity = '1';
      }
    });

    return () => {
      globe.destroy();
      window.removeEventListener('resize', onResize);
    };
  }, []);

  return (
    <div className="w-full aspect-square">
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          contain: 'layout paint size',
          opacity: 0,
          transition: 'opacity 1s ease',
        }}
      />
    </div>
  );
}
