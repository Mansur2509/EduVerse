"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

import { usePrefersReducedMotion } from "@/shared/ui/use-reduced-motion";

export type GlobeSceneMarker = {
  id: string;
  label: string;
  lat: number;
  lon: number;
};

type GlobeThreeSceneProps = {
  activeId: string;
  ariaLabel: string;
  fallbackLabel: string;
  markers: GlobeSceneMarker[];
  onSelect: (id: string) => void;
  renderedLabel: string;
};

function latLonToVector3(lat: number, lon: number, radius: number) {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lon + 180);

  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

function canUseWebGl() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

type LatLon = readonly [number, number];

type GlobeOutline = {
  closed?: boolean;
  color?: string;
  opacity?: number;
  points: LatLon[];
};

type TopologyArc = Array<readonly [number, number]>;

type WorldTopologyTransform = {
  scale: readonly [number, number];
  translate: readonly [number, number];
};

type WorldPolygonGeometry = {
  arcs: number[][];
  type: "Polygon";
};

type WorldMultiPolygonGeometry = {
  arcs: number[][][];
  type: "MultiPolygon";
};

type WorldGeometry = WorldPolygonGeometry | WorldMultiPolygonGeometry;

type WorldTopology = {
  arcs: TopologyArc[];
  objects?: {
    countries?: {
      geometries: WorldGeometry[];
      type: "GeometryCollection";
    };
  };
  transform?: WorldTopologyTransform;
  type: "Topology";
};

const GLOBE_OUTLINES: GlobeOutline[] = [
  {
    closed: true,
    opacity: 0.34,
    points: [
      [72, -168],
      [69, -128],
      [58, -60],
      [43, -66],
      [27, -81],
      [14, -92],
      [20, -111],
      [34, -124],
      [52, -132],
      [72, -168]
    ]
  },
  {
    closed: true,
    opacity: 0.26,
    points: [
      [50, -124],
      [49, -67],
      [31, -81],
      [25, -97],
      [32, -117],
      [42, -124],
      [50, -124]
    ]
  },
  {
    closed: true,
    opacity: 0.26,
    points: [
      [69, -141],
      [70, -62],
      [55, -53],
      [49, -67],
      [50, -124],
      [60, -141],
      [69, -141]
    ]
  },
  {
    closed: true,
    opacity: 0.34,
    points: [
      [71, -10],
      [64, 32],
      [52, 41],
      [41, 29],
      [36, 10],
      [43, -9],
      [55, -11],
      [62, -25],
      [71, -10]
    ]
  },
  {
    closed: true,
    color: "#d8a340",
    opacity: 0.5,
    points: [
      [58.8, -5.8],
      [56.5, -2.0],
      [52.0, 1.5],
      [50.0, -4.7],
      [53.7, -8.2],
      [58.8, -5.8]
    ]
  },
  {
    closed: true,
    color: "#d8a340",
    opacity: 0.42,
    points: [
      [46.6, 7.5],
      [44.6, 12.2],
      [41.7, 14.7],
      [38.2, 16.2],
      [37.0, 13.2],
      [40.6, 8.6],
      [44.3, 7.2],
      [46.6, 7.5]
    ]
  },
  {
    closed: true,
    opacity: 0.34,
    points: [
      [78, 45],
      [64, 97],
      [57, 140],
      [40, 146],
      [23, 113],
      [8, 78],
      [26, 44],
      [45, 33],
      [61, 54],
      [78, 45]
    ]
  },
  {
    closed: true,
    color: "#d8a340",
    opacity: 0.48,
    points: [
      [42.5, 124.2],
      [40.2, 129.5],
      [35.2, 129.3],
      [33.1, 126.5],
      [36.5, 124.4],
      [42.5, 124.2]
    ]
  },
  {
    closed: true,
    color: "#d8a340",
    opacity: 0.5,
    points: [
      [1.65, 103.55],
      [1.52, 104.08],
      [1.16, 104.0],
      [1.08, 103.62],
      [1.34, 103.45],
      [1.65, 103.55]
    ]
  },
  {
    closed: true,
    opacity: 0.28,
    points: [
      [36, -17],
      [31, 32],
      [10, 42],
      [-33, 28],
      [-35, 18],
      [0, 8],
      [12, -17],
      [36, -17]
    ]
  }
];

function createGlobeOutline(outline: GlobeOutline, radius: number) {
  const points = outline.closed ? [...outline.points, outline.points[0]] : outline.points;
  const geometry = new THREE.BufferGeometry().setFromPoints(
    points.map(([lat, lon]) => latLonToVector3(lat, lon, radius))
  );
  return new THREE.Line(
    geometry,
    new THREE.LineBasicMaterial({
      color: outline.color ?? "#f8f3e8",
      depthWrite: false,
      opacity: outline.opacity ?? 0.3,
      transparent: true
    })
  );
}

function createFallbackBorderGroup(radius: number) {
  const group = new THREE.Group();
  GLOBE_OUTLINES.forEach((outline) => {
    group.add(createGlobeOutline(outline, radius));
  });
  return group;
}

function decodeTopologyArcs(topology: WorldTopology) {
  const transform = topology.transform;
  if (!transform) return [];

  return topology.arcs.map((arc) => {
    let x = 0;
    let y = 0;
    return arc.map(([deltaX, deltaY]) => {
      x += deltaX;
      y += deltaY;
      const lon = transform.translate[0] + x * transform.scale[0];
      const lat = transform.translate[1] + y * transform.scale[1];
      return [lat, lon] as const;
    });
  });
}

function resolveTopologyArc(decodedArcs: LatLon[][], arcIndex: number) {
  const arc = decodedArcs[arcIndex >= 0 ? arcIndex : ~arcIndex] ?? [];
  return arcIndex >= 0 ? arc : [...arc].reverse();
}

function stitchTopologyRing(decodedArcs: LatLon[][], ringArcs: number[]) {
  const ring: LatLon[] = [];
  ringArcs.forEach((arcIndex) => {
    const arc = resolveTopologyArc(decodedArcs, arcIndex);
    arc.forEach((point, pointIndex) => {
      if (ring.length > 0 && pointIndex === 0) return;
      ring.push(point);
    });
  });
  return ring;
}

function appendRingSegments(positions: number[], ring: LatLon[], radius: number) {
  if (ring.length < 2) return;

  ring.forEach((point, index) => {
    const next = index === ring.length - 1 ? ring[0] : ring[index + 1];
    if (!next || Math.abs(point[1] - next[1]) > 180) return;

    const from = latLonToVector3(point[0], point[1], radius);
    const to = latLonToVector3(next[0], next[1], radius);
    positions.push(from.x, from.y, from.z, to.x, to.y, to.z);
  });
}

function createCountryBorderLines(topology: WorldTopology, radius: number) {
  const countries = topology.objects?.countries?.geometries;
  if (!countries?.length) return null;

  const decodedArcs = decodeTopologyArcs(topology);
  if (!decodedArcs.length) return null;

  const positions: number[] = [];
  countries.forEach((geometry) => {
    if (geometry.type === "Polygon") {
      geometry.arcs.forEach((ringArcs) => {
        appendRingSegments(positions, stitchTopologyRing(decodedArcs, ringArcs), radius);
      });
      return;
    }

    geometry.arcs.forEach((polygon) => {
      polygon.forEach((ringArcs) => {
        appendRingSegments(positions, stitchTopologyRing(decodedArcs, ringArcs), radius);
      });
    });
  });

  if (!positions.length) return null;

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  return new THREE.LineSegments(
    geometry,
    new THREE.LineBasicMaterial({
      color: "#f8f3e8",
      depthWrite: false,
      opacity: 0.28,
      transparent: true
    })
  );
}

function disposeObject3D(object: THREE.Object3D) {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
      child.geometry.dispose();
      if (Array.isArray(child.material)) {
        child.material.forEach((material) => material.dispose());
      } else {
        child.material.dispose();
      }
    }
  });
}

export function GlobeThreeScene({
  activeId,
  ariaLabel,
  fallbackLabel,
  markers,
  onSelect,
  renderedLabel
}: GlobeThreeSceneProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const markerMeshesRef = useRef<Map<string, THREE.Mesh>>(new Map());
  const selectedIdRef = useRef(activeId);
  const onSelectRef = useRef(onSelect);
  const focusTargetRef = useRef<{ x: number; y: number; until: number }>({ x: 0, y: 0, until: 0 });
  const prefersReducedMotion = usePrefersReducedMotion();
  const [status, setStatus] = useState<"loading" | "ready" | "fallback">("loading");

  useEffect(() => {
    selectedIdRef.current = activeId;
    const activeMarker = markers.find((marker) => marker.id === activeId);
    if (activeMarker) {
      focusTargetRef.current = {
        x: THREE.MathUtils.clamp(THREE.MathUtils.degToRad(activeMarker.lat * -0.32), -0.55, 0.18),
        y: THREE.MathUtils.degToRad(-activeMarker.lon - 90),
        until: performance.now() + (prefersReducedMotion ? 0 : 1500)
      };
    }
    markerMeshesRef.current.forEach((mesh, id) => {
      const selected = id === activeId;
      mesh.scale.setScalar(selected ? 1.55 : 1);
      const material = mesh.material;
      if (material instanceof THREE.MeshStandardMaterial) {
        material.color.set(selected ? "#d8a340" : "#f8f3e8");
        material.emissive.set(selected ? "#7a0b22" : "#153c6a");
        material.emissiveIntensity = selected ? 0.38 : 0.16;
      }
    });
  }, [activeId, markers, prefersReducedMotion]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    const canvasElement = canvasRef.current;
    if (!canvasElement || !canUseWebGl()) {
      setStatus("fallback");
      return;
    }
    const canvasNode: HTMLCanvasElement = canvasElement;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        canvas: canvasNode,
        powerPreference: "low-power"
      });
    } catch {
      setStatus("fallback");
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 0.32, 7.5);

    const root = new THREE.Group();
    root.rotation.x = THREE.MathUtils.degToRad(-12);
    root.rotation.y = THREE.MathUtils.degToRad(24);
    scene.add(root);

    const atmosphere = new THREE.Mesh(
      new THREE.SphereGeometry(2.34, 64, 32),
      new THREE.MeshBasicMaterial({
        color: "#3c8dce",
        opacity: 0.14,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    root.add(atmosphere);

    const globe = new THREE.Mesh(
      new THREE.SphereGeometry(2.12, 96, 48),
      new THREE.MeshStandardMaterial({
        color: "#11243c",
        metalness: 0.06,
        roughness: 0.62
      })
    );
    root.add(globe);

    const wire = new THREE.LineSegments(
      new THREE.WireframeGeometry(new THREE.SphereGeometry(2.135, 32, 18)),
      new THREE.LineBasicMaterial({
        color: "#f8f3e8",
        opacity: 0.16,
        transparent: true
      })
    );
    root.add(wire);

    const land = new THREE.Group();
    [
      { lat: 42, lon: -95, scale: [0.5, 0.12, 0.22], rotate: 0.2 },
      { lat: 52, lon: -3, scale: [0.26, 0.07, 0.12], rotate: -0.3 },
      { lat: 45, lon: 11, scale: [0.24, 0.07, 0.12], rotate: 0.35 },
      { lat: 36, lon: 128, scale: [0.28, 0.07, 0.12], rotate: -0.18 },
      { lat: 1.3, lon: 104, scale: [0.2, 0.05, 0.1], rotate: 0.1 },
      { lat: 54, lon: -106, scale: [0.42, 0.1, 0.18], rotate: -0.2 }
    ].forEach((shape) => {
      const position = latLonToVector3(shape.lat, shape.lon, 2.155);
      const patch = new THREE.Mesh(
        new THREE.SphereGeometry(0.42, 20, 10),
        new THREE.MeshStandardMaterial({
          color: "#1d5d7a",
          opacity: 0.58,
          transparent: true,
          roughness: 0.7
        })
      );
      patch.position.copy(position);
      patch.lookAt(0, 0, 0);
      patch.rotateZ(shape.rotate);
      patch.scale.set(shape.scale[0], shape.scale[1], shape.scale[2]);
      land.add(patch);
    });
    root.add(land);

    const fallbackBorderGroup = createFallbackBorderGroup(2.182);
    root.add(fallbackBorderGroup);

    const markerGeometry = new THREE.SphereGeometry(0.075, 18, 12);
    const markerMeshes = new Map<string, THREE.Mesh>();
    markers.forEach((marker) => {
      const selected = marker.id === selectedIdRef.current;
      const markerMesh = new THREE.Mesh(
        markerGeometry,
        new THREE.MeshStandardMaterial({
          color: selected ? "#d8a340" : "#f8f3e8",
          emissive: selected ? "#7a0b22" : "#153c6a",
          emissiveIntensity: selected ? 0.38 : 0.16,
          metalness: 0.12,
          roughness: 0.28
        })
      );
      markerMesh.position.copy(latLonToVector3(marker.lat, marker.lon, 2.32));
      markerMesh.scale.setScalar(selected ? 1.55 : 1);
      markerMesh.userData = { id: marker.id };
      root.add(markerMesh);
      markerMeshes.set(marker.id, markerMesh);
    });
    markerMeshesRef.current = markerMeshes;

    const selectedRing = new THREE.Mesh(
      new THREE.TorusGeometry(0.18, 0.008, 8, 36),
      new THREE.MeshBasicMaterial({ color: "#d8a340", opacity: 0.8, transparent: true })
    );
    root.add(selectedRing);

    const ambient = new THREE.AmbientLight("#f8f3e8", 0.8);
    const key = new THREE.DirectionalLight("#ffffff", 2.35);
    key.position.set(-2.8, 3.4, 5.8);
    const rim = new THREE.DirectionalLight("#4e9bd4", 1.45);
    rim.position.set(3.8, -0.6, -2.2);
    scene.add(ambient, key, rim);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const drag = {
      active: false,
      lastX: 0,
      lastY: 0,
      moved: false,
      velocityX: 0,
      velocityY: 0
    };
    let frameId = 0;
    let readyReported = false;
    let visible = true;
    let tabVisible = !document.hidden;
    let lastFrame = 0;
    let disposed = false;

    async function loadCountryBorders() {
      try {
        const response = await fetch("/data/countries-110m.json", { cache: "force-cache" });
        if (!response.ok) return;
        const topology = (await response.json()) as WorldTopology;
        const countryBorders = createCountryBorderLines(topology, 2.19);
        if (!countryBorders || disposed) {
          countryBorders?.geometry.dispose();
          if (countryBorders?.material instanceof THREE.Material) {
            countryBorders.material.dispose();
          }
          return;
        }
        root.remove(fallbackBorderGroup);
        disposeObject3D(fallbackBorderGroup);
        root.add(countryBorders);
      } catch {
        // Keep the handcrafted fallback contours when the local atlas cannot be loaded.
      }
    }

    function shortestAngleTo(current: number, target: number) {
      return Math.atan2(Math.sin(target - current), Math.cos(target - current));
    }

    function syncSelectedRing() {
      const selected = markerMeshes.get(selectedIdRef.current);
      if (!selected) return;
      selectedRing.visible = true;
      selectedRing.position.copy(selected.position);
      selectedRing.lookAt(camera.position);
    }

    function setRendererSize() {
      const rect = canvasNode.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      const navigatorWithHints = navigator as Navigator & { deviceMemory?: number };
      const lowPower =
        navigatorWithHints.deviceMemory !== undefined && navigatorWithHints.deviceMemory <= 4;
      const pixelRatio = Math.min(window.devicePixelRatio || 1, lowPower || width < 720 ? 1.25 : 1.75);
      renderer.setPixelRatio(pixelRatio);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    function renderFrame(now: number) {
      frameId = window.requestAnimationFrame(renderFrame);
      // The very first frame always renders once, even if the tab/canvas
      // isn't visible yet (e.g. opened in a background tab, or a browser
      // that reports `document.hidden` briefly during preload). Without
      // this, a page that never fires `visibilitychange` correctly would
      // stay on the "loading" status forever with no way to recover.
      // Every later frame still respects the pause-when-hidden/off-screen
      // behavior as intended.
      if (readyReported && (!visible || !tabVisible)) return;
      if (readyReported && now - lastFrame < (prefersReducedMotion ? 500 : 32)) return;
      lastFrame = now;

      if (!prefersReducedMotion) {
        const shouldFocus = focusTargetRef.current.until > now;
        if (!drag.active && shouldFocus) {
          root.rotation.x += (focusTargetRef.current.x - root.rotation.x) * 0.075;
          root.rotation.y += shortestAngleTo(root.rotation.y, focusTargetRef.current.y) * 0.075;
          drag.velocityX = 0;
          drag.velocityY = 0;
        } else if (!drag.active) {
          root.rotation.y += drag.velocityX;
          root.rotation.x += drag.velocityY;
          drag.velocityX *= 0.94;
          drag.velocityY *= 0.92;
          if (Math.abs(drag.velocityX) < 0.0015) {
            root.rotation.y += 0.0024;
          }
        }
        root.rotation.x = THREE.MathUtils.clamp(root.rotation.x, -0.72, 0.38);
      }

      atmosphere.rotation.y = root.rotation.y * 0.72;
      land.rotation.y = Math.sin(now * 0.00018) * 0.02;
      syncSelectedRing();
      renderer.render(scene, camera);
      if (!readyReported) {
        readyReported = true;
        setStatus("ready");
      }
    }

    function handlePointerDown(event: PointerEvent) {
      if (prefersReducedMotion) return;
      canvasNode.setPointerCapture(event.pointerId);
      drag.active = true;
      drag.moved = false;
      drag.lastX = event.clientX;
      drag.lastY = event.clientY;
      drag.velocityX = 0;
      drag.velocityY = 0;
    }

    function handlePointerMove(event: PointerEvent) {
      if (!drag.active || prefersReducedMotion) return;
      const deltaX = event.clientX - drag.lastX;
      const deltaY = event.clientY - drag.lastY;
      drag.lastX = event.clientX;
      drag.lastY = event.clientY;
      drag.moved = drag.moved || Math.abs(deltaX) + Math.abs(deltaY) > 5;
      const rotateY = deltaX * 0.006;
      const rotateX = deltaY * 0.004;
      root.rotation.y += rotateY;
      root.rotation.x = THREE.MathUtils.clamp(root.rotation.x + rotateX, -0.72, 0.38);
      drag.velocityX = rotateY;
      drag.velocityY = rotateX;
      focusTargetRef.current.until = 0;
    }

    function selectMarkerFromPointer(event: PointerEvent) {
      const rect = canvasNode.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects([...markerMeshes.values()]);
      const id = hits[0]?.object.userData.id;
      if (typeof id === "string") onSelectRef.current(id);
    }

    function handlePointerUp(event: PointerEvent) {
      if (canvasNode.hasPointerCapture(event.pointerId)) {
        canvasNode.releasePointerCapture(event.pointerId);
      }
      const wasDrag = drag.moved;
      drag.active = false;
      if (!wasDrag) selectMarkerFromPointer(event);
    }

    function handleVisibilityChange() {
      tabVisible = !document.hidden;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        visible = entry?.isIntersecting ?? true;
      },
      { threshold: 0.1 }
    );
    observer.observe(canvasNode);

    const resizeObserver = new ResizeObserver(setRendererSize);
    resizeObserver.observe(canvasNode);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    canvasNode.addEventListener("pointerdown", handlePointerDown);
    canvasNode.addEventListener("pointermove", handlePointerMove);
    canvasNode.addEventListener("pointerup", handlePointerUp);
    canvasNode.addEventListener("pointercancel", handlePointerUp);

    setRendererSize();
    syncSelectedRing();
    frameId = window.requestAnimationFrame(renderFrame);
    void loadCountryBorders();

    // Safety net: the "first frame always renders" fix above covers the
    // normal cases, but if requestAnimationFrame itself never gets serviced
    // for some reason, fall back to the accessible SVG view instead of an
    // indefinite loading state.
    const readyTimeoutId = window.setTimeout(() => {
      if (!disposed && !readyReported) {
        setStatus("fallback");
      }
    }, 4000);

    return () => {
      disposed = true;
      window.clearTimeout(readyTimeoutId);
      window.cancelAnimationFrame(frameId);
      observer.disconnect();
      resizeObserver.disconnect();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      canvasNode.removeEventListener("pointerdown", handlePointerDown);
      canvasNode.removeEventListener("pointermove", handlePointerMove);
      canvasNode.removeEventListener("pointerup", handlePointerUp);
      canvasNode.removeEventListener("pointercancel", handlePointerUp);
      markerGeometry.dispose();
      markerMeshes.forEach((mesh) => {
        if (mesh.material instanceof THREE.Material) mesh.material.dispose();
      });
      disposeObject3D(scene);
      renderer.dispose();
      markerMeshesRef.current = new Map();
    };
  }, [markers, prefersReducedMotion]);

  return (
    <div className="absolute inset-0">
      {status === "fallback" ? (
        <div className="grid h-full place-items-center px-6 text-center text-sm font-semibold text-white/75">
          {fallbackLabel}
        </div>
      ) : null}
      {status === "loading" ? (
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-xs font-bold uppercase tracking-[0.16em] text-white/55">
          {renderedLabel}
        </div>
      ) : null}
      <canvas
        aria-label={ariaLabel}
        className={`size-full touch-none ${status === "fallback" ? "pointer-events-none opacity-0" : ""}`}
        data-active-country={activeId}
        data-globe-render-status={status}
        ref={canvasRef}
      />
    </div>
  );
}
