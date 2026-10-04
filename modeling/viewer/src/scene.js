import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const directions = {
  front: new THREE.Vector3(0, 0.04, 1),
  side: new THREE.Vector3(1, 0.04, 0),
  back: new THREE.Vector3(0, 0.04, -1),
  overview: new THREE.Vector3(0.38, 0.08, 1).normalize(),
};

function disposeModel(model) {
  const materials = new Set();
  model.traverse((object) => {
    if (!object.isMesh) return;
    object.geometry.dispose();
    for (const material of [].concat(object.material)) materials.add(material);
  });
  for (const material of materials) {
    for (const value of Object.values(material)) {
      if (value?.isTexture) value.dispose();
    }
    material.dispose();
  }
}

export function createViewer(host, { onReady, onProgress, onError, onInteract }) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    onError('The 3D view could not start. Enable hardware acceleration in your browser, then reload.');
    return null;
  }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  const canvas = renderer.domElement;
  canvas.tabIndex = 0;
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', 'Interactive 3D model of the Kintra knee sleeves on a standing mannequin. Use the view and zoom buttons, or arrow keys to rotate.');
  host.appendChild(canvas);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 30);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.enablePan = false;
  controls.minPolarAngle = 0.16;
  controls.maxPolarAngle = Math.PI - 0.16;
  controls.autoRotateSpeed = 0.65;

  const environment = new RoomEnvironment();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const environmentMap = pmrem.fromScene(environment, 0.04);
  scene.environment = environmentMap.texture;
  scene.environmentIntensity = 0.45;
  environment.dispose();
  pmrem.dispose();

  scene.add(new THREE.HemisphereLight(0xffffff, 0x37303c, 0.65));
  for (const [color, intensity, position] of [
    [0xffeee0, 1.6, [2, 3, 3]],
    [0xdce9ff, 0.7, [-2, 1.5, 1]],
    [0xffffff, 1.2, [0, 2, -3]],
  ]) {
    const light = new THREE.DirectionalLight(color, intensity);
    light.position.set(...position);
    scene.add(light);
  }

  // A soft contact shadow without an expensive shadow pass through every yarn.
  const shadowCanvas = document.createElement('canvas');
  shadowCanvas.width = shadowCanvas.height = 128;
  const context = shadowCanvas.getContext('2d');
  const gradient = context.createRadialGradient(64, 64, 6, 64, 64, 64);
  gradient.addColorStop(0, 'rgba(0,0,0,0.6)');
  gradient.addColorStop(1, 'rgba(0,0,0,0)');
  context.fillStyle = gradient;
  context.fillRect(0, 0, 128, 128);
  const shadowTexture = new THREE.CanvasTexture(shadowCanvas);
  const shadowMaterial = new THREE.MeshBasicMaterial({
    map: shadowTexture, transparent: true, depthWrite: false,
  });
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(0.95, 0.65), shadowMaterial);
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -0.002;
  scene.add(shadow);

  let model;
  let disposed = false;
  let mode = 'body';
  let view = 'overview';
  let bodyBounds;
  let kneeBounds;
  let previousTime;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  controls.enableDamping = !reducedMotion.matches;

  function fit() {
    if (!model) return;
    const bounds = mode === 'knee' ? kneeBounds : bodyBounds;
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const verticalFov = THREE.MathUtils.degToRad(camera.fov);
    const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
    const distance = 1.2 * Math.max(
      size.y / (2 * Math.tan(verticalFov / 2)),
      Math.max(size.x, size.z) / (2 * Math.tan(horizontalFov / 2)),
    ) + size.z / 2;
    controls.target.copy(center);
    controls.cursor.copy(center);
    controls.minDistance = mode === 'knee' ? 0.22 : 0.4;
    controls.maxDistance = distance * 2.4;
    camera.position.copy(center).addScaledVector(directions[view] || directions.overview, distance);
    camera.lookAt(center);
    controls.update();
  }

  function resize() {
    const width = host.clientWidth;
    const height = host.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    fit();
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  resize();

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  loader.load(`${import.meta.env.BASE_URL}models/kintra.glb`, (gltf) => {
    if (disposed) {
      disposeModel(gltf.scene);
      return;
    }
    model = gltf.scene;
    const originalBounds = new THREE.Box3().setFromObject(model);
    const center = originalBounds.getCenter(new THREE.Vector3());
    model.position.set(-center.x, -originalBounds.min.y, -center.z);
    scene.add(model);
    model.updateMatrixWorld(true);
    bodyBounds = new THREE.Box3().setFromObject(model);
    kneeBounds = new THREE.Box3();
    let meshCount = 0;
    let triangles = 0;
    model.traverse((object) => {
      if (!object.isMesh) return;
      meshCount++;
      triangles += (object.geometry.index?.count || object.geometry.attributes.position.count) / 3;
      if (object.name.startsWith('Left') || object.name.startsWith('Right')) {
        kneeBounds.union(new THREE.Box3().setFromObject(object));
      }
    });
    if (kneeBounds.isEmpty()) kneeBounds.copy(bodyBounds);
    // Useful for checking that the actual export loaded, without visible technical UI.
    canvas.dataset.meshes = meshCount;
    canvas.dataset.triangles = triangles;
    fit();
    onReady();
  }, (event) => {
    if (!disposed && event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100));
  }, (error) => {
    if (disposed) return;
    console.error('Kintra model loading failed:', error);
    onError('The model could not load. Check your connection and reload the viewer.');
  });

  const interact = () => {
    view = 'custom';
    onInteract();
  };
  controls.addEventListener('start', interact);

  function zoom(factor) {
    const offset = camera.position.clone().sub(controls.target);
    offset.setLength(THREE.MathUtils.clamp(offset.length() * factor, controls.minDistance, controls.maxDistance));
    camera.position.copy(controls.target).add(offset);
    controls.update();
  }

  function orbit(horizontal, vertical = 0) {
    const spherical = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
    spherical.theta += horizontal;
    spherical.phi = THREE.MathUtils.clamp(spherical.phi + vertical, controls.minPolarAngle, controls.maxPolarAngle);
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));
    controls.update();
    interact();
  }

  function keydown(event) {
    if (!model) return;
    const actions = {
      ArrowLeft: () => orbit(-0.12), ArrowRight: () => orbit(0.12),
      ArrowUp: () => orbit(0, -0.12), ArrowDown: () => orbit(0, 0.12),
      '+': () => zoom(0.85), '=': () => zoom(0.85), '-': () => zoom(1.18),
    };
    if (actions[event.key]) {
      event.preventDefault();
      actions[event.key]();
    }
  }
  canvas.addEventListener('keydown', keydown);

  function motionChange() {
    controls.enableDamping = !reducedMotion.matches;
    if (reducedMotion.matches) controls.autoRotate = false;
  }
  reducedMotion.addEventListener('change', motionChange);

  renderer.setAnimationLoop((time) => {
    const delta = previousTime === undefined ? 0 : Math.min((time - previousTime) / 1000, 0.1);
    previousTime = time;
    controls.update(delta);
    renderer.render(scene, camera);
  });

  return {
    setMode(nextMode) { mode = nextMode; fit(); },
    setView(nextView) { view = nextView; fit(); },
    setAutoRotate(value) { controls.autoRotate = value; },
    zoom,
    orbit,
    dispose() {
      disposed = true;
      renderer.setAnimationLoop(null);
      resizeObserver.disconnect();
      reducedMotion.removeEventListener('change', motionChange);
      canvas.removeEventListener('keydown', keydown);
      controls.removeEventListener('start', interact);
      controls.dispose();
      if (model) disposeModel(model);
      shadow.geometry.dispose();
      shadowMaterial.dispose();
      shadowTexture.dispose();
      environmentMap.dispose();
      renderer.dispose();
      canvas.remove();
    },
  };
}
