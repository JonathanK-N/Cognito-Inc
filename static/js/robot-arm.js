/* Cellule robotisée en 3D (Three.js) : bras industriel 6 axes qui prend des cartons sur un convoyeur
   et les palettise. Cinématique inverse analytique, trajectoires en espace articulaire, ombres et reflets PBR. */
import * as THREE from '../vendor/three/three.module.min.js';
import { RoomEnvironment } from '../vendor/three/RoomEnvironment.js';
import { RoundedBoxGeometry } from '../vendor/three/RoundedBoxGeometry.js';

export function mountRobotCell(host) {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
  } catch (e) {
    return false;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.className = 'robot-canvas';
  renderer.domElement.setAttribute('aria-hidden', 'true');
  host.appendChild(renderer.domElement);

  const BG = 0x0a1626;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BG);
  scene.fog = new THREE.Fog(BG, 5.5, 10);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;

  const camera = new THREE.PerspectiveCamera(30, 16 / 9, 0.1, 30);
  const target = new THREE.Vector3(-0.15, 0.62, 0.3);

  /* Éclairage */
  scene.add(new THREE.HemisphereLight(0xbfd6ff, 0x0b1220, 0.55));
  const key = new THREE.DirectionalLight(0xffffff, 2.6);
  key.position.set(2.4, 4.2, 2.2);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.left = -2.6; key.shadow.camera.right = 2.6;
  key.shadow.camera.top = 2.6; key.shadow.camera.bottom = -2.6;
  key.shadow.camera.near = 1; key.shadow.camera.far = 9;
  key.shadow.bias = -0.0004; key.shadow.normalBias = 0.02; key.shadow.radius = 3;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x6f9bff, 1.4);
  rim.position.set(-3, 2.2, -2.5);
  scene.add(rim);

  /* Matériaux */
  const M = {
    paint: new THREE.MeshPhysicalMaterial({ color: 0xe8730c, roughness: 0.38, metalness: 0.15, clearcoat: 0.7, clearcoatRoughness: 0.22 }),
    dark: new THREE.MeshStandardMaterial({ color: 0x2b3038, roughness: 0.45, metalness: 0.65 }),
    steel: new THREE.MeshStandardMaterial({ color: 0xc4cad2, roughness: 0.28, metalness: 1 }),
    alu: new THREE.MeshStandardMaterial({ color: 0x9aa4af, roughness: 0.35, metalness: 0.85 }),
    rubber: new THREE.MeshStandardMaterial({ color: 0x121417, roughness: 0.85, metalness: 0 }),
    floor: new THREE.MeshStandardMaterial({ color: 0x141b25, roughness: 0.92, metalness: 0.05 }),
    wood: new THREE.MeshStandardMaterial({ color: 0x8c6a45, roughness: 0.9, metalness: 0 }),
    card: new THREE.MeshStandardMaterial({ color: 0xc69a62, roughness: 0.88, metalness: 0 }),
    tape: new THREE.MeshStandardMaterial({ color: 0xf2c230, roughness: 0.7, metalness: 0 }),
    boxTape: new THREE.MeshStandardMaterial({ color: 0xb08a55, roughness: 0.5 }),
    label: new THREE.MeshStandardMaterial({ color: 0x2558f0, roughness: 0.6, metalness: 0 })
  };

  function mesh(geo, mat, parent, x, y, z) {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x || 0, y || 0, z || 0);
    m.castShadow = true;
    m.receiveShadow = true;
    if (parent) parent.add(m);
    return m;
  }
  const rbox = (w, h, d, r) => new RoundedBoxGeometry(w, h, d, 4, r || 0.03);
  const cylX = (r, len, seg) => new THREE.CylinderGeometry(r, r, len, seg || 40).rotateZ(Math.PI / 2);
  const cylZ = (r, len, seg) => new THREE.CylinderGeometry(r, r, len, seg || 40).rotateX(Math.PI / 2);
  const cylY = (r, len, seg, r2) => new THREE.CylinderGeometry(r2 === undefined ? r : r2, r, len, seg || 48);

  /* Sol, marquage de sécurité */
  const floor = mesh(new THREE.PlaneGeometry(14, 14), M.floor, scene);
  floor.rotation.x = -Math.PI / 2;
  floor.castShadow = false;
  const tapeMat = M.tape;
  [[0, 1.75, 3.6, 0.05], [0, -1.55, 3.6, 0.05], [1.78, 0.1, 0.05, 3.35], [-1.78, 0.1, 0.05, 3.35]].forEach(function (t) {
    const s = mesh(new THREE.PlaneGeometry(t[2], t[3]), tapeMat, scene, t[0], 0.002, t[1]);
    s.rotation.x = -Math.PI / 2; s.castShadow = false;
  });

  /* ─── Robot ─── */
  const A1 = 0.18, H0 = 0.75, L2 = 0.9, L3 = 0.86, D6 = 0.23;

  const pedestal = new THREE.Group();
  scene.add(pedestal);
  mesh(cylY(0.36, 0.06, 56), M.dark, pedestal, 0, 0.03, 0);
  mesh(cylY(0.3, 0.2, 56), M.dark, pedestal, 0, 0.16, 0);
  for (let i = 0; i < 8; i += 1) {
    const a = i / 8 * Math.PI * 2;
    mesh(cylY(0.018, 0.03, 12), M.steel, pedestal, Math.cos(a) * 0.32, 0.07, Math.sin(a) * 0.32);
  }

  const j1 = new THREE.Group(); j1.position.y = 0.26; scene.add(j1);
  mesh(cylY(0.3, 0.1, 64, 0.27), M.paint, j1, 0, 0.05, 0);
  mesh(cylY(0.305, 0.02, 64), M.dark, j1, 0, 0.005, 0);
  mesh(rbox(0.5, 0.36, 0.46, 0.06), M.paint, j1, 0.07, 0.27, 0);
  mesh(rbox(0.22, 0.2, 0.2, 0.03), M.dark, j1, -0.22, 0.28, 0);           // moteur J1
  mesh(cylZ(0.17, 0.12), M.paint, j1, A1, H0 - 0.26, 0.26);               // carter J2
  mesh(cylZ(0.12, 0.05), M.dark, j1, A1, H0 - 0.26, 0.345);
  mesh(cylZ(0.17, 0.12), M.paint, j1, A1, H0 - 0.26, -0.26);
  mesh(cylZ(0.11, 0.18), M.dark, j1, A1, H0 - 0.26, -0.39);               // moteur J2

  const j2 = new THREE.Group(); j2.position.set(A1, H0 - 0.26, 0); j1.add(j2);
  mesh(cylZ(0.16, 0.38), M.paint, j2);
  mesh(rbox(0.24, L2 + 0.06, 0.2, 0.07), M.paint, j2, 0, L2 / 2, 0);
  mesh(rbox(0.2, L2 * 0.5, 0.03, 0.012), M.paint, j2, 0, L2 * 0.48, 0.105);  // carénage
  mesh(rbox(0.2, L2 * 0.5, 0.03, 0.012), M.paint, j2, 0, L2 * 0.48, -0.105);
  const cable1 = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.13, 0.05, 0.05), new THREE.Vector3(-0.17, 0.3, 0.06), new THREE.Vector3(-0.16, 0.65, 0.06), new THREE.Vector3(-0.1, L2 + 0.02, 0.07)]);
  mesh(new THREE.TubeGeometry(cable1, 40, 0.026, 12), M.rubber, j2);

  const j3 = new THREE.Group(); j3.position.set(0, L2, 0); j2.add(j3);
  mesh(cylZ(0.15, 0.32), M.paint, j3);
  mesh(cylZ(0.1, 0.06), M.dark, j3, 0, 0, 0.18);
  mesh(rbox(0.36, 0.26, 0.26, 0.06), M.paint, j3, -0.06, 0.04, 0);
  mesh(cylX(0.07, 0.16), M.dark, j3, -0.3, 0.07, 0.06);                    // moteurs poignet
  mesh(cylX(0.06, 0.14), M.dark, j3, -0.29, 0.0, -0.07);
  mesh(cylX(0.11, 0.5, 48), M.paint, j3, 0.38, 0.03, 0);
  mesh(new THREE.CylinderGeometry(0.085, 0.11, 0.14, 48).rotateZ(-Math.PI / 2), M.paint, j3, 0.7, 0.03, 0);
  const cable2 = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.12, 0.17, 0.02), new THREE.Vector3(0.2, 0.16, 0.02), new THREE.Vector3(0.55, 0.13, 0.0), new THREE.Vector3(0.74, 0.09, 0.0)]);
  mesh(new THREE.TubeGeometry(cable2, 40, 0.02, 12), M.rubber, j3);

  const j4 = new THREE.Group(); j4.position.set(L3 - 0.1, 0, 0); j3.add(j4);
  mesh(cylX(0.08, 0.06), M.dark, j4, 0.0, 0, 0);
  mesh(rbox(0.14, 0.15, 0.2, 0.05), M.paint, j4, 0.07, 0, 0);

  const j5 = new THREE.Group(); j5.position.set(0.1, 0, 0); j4.add(j5);
  mesh(cylZ(0.065, 0.22), M.dark, j5);

  const j6 = new THREE.Group(); j6.position.set(0.075, 0, 0); j5.add(j6);
  mesh(cylX(0.055, 0.03), M.steel, j6, 0.0, 0, 0);
  mesh(cylX(0.045, 0.03), M.dark, j6, 0.03, 0, 0);
  mesh(rbox(0.06, 0.1, 0.2, 0.012), M.dark, j6, 0.075, 0, 0);
  mesh(rbox(0.012, 0.03, 0.22, 0.004), M.steel, j6, 0.108, 0, 0);
  const fingerGeo = rbox(0.09, 0.05, 0.022, 0.006);
  const fingerA = mesh(fingerGeo, M.steel, j6, 0.155, 0, 0.1);
  const fingerB = mesh(fingerGeo, M.steel, j6, 0.155, 0, -0.1);
  const padGeo = rbox(0.05, 0.04, 0.006, 0.002);
  mesh(padGeo, M.rubber, fingerA, 0.012, 0, -0.013);
  mesh(padGeo, M.rubber, fingerB, 0.012, 0, 0.013);
  const grip = new THREE.Object3D(); grip.position.set(D6 - 0.075, 0, 0); j6.add(grip);   // centre de préhension

  /* Colonne lumineuse */
  const beacon = new THREE.Group(); beacon.position.set(-1.55, 0, -1.3); scene.add(beacon);
  mesh(cylY(0.02, 1.3, 16), M.alu, beacon, 0, 0.65, 0);
  const lampGreen = new THREE.MeshStandardMaterial({ color: 0x1a7a46, emissive: 0x2bff8a, emissiveIntensity: 1.6, roughness: 0.3 });
  const lampAmber = new THREE.MeshStandardMaterial({ color: 0x5a4210, emissive: 0xffb020, emissiveIntensity: 0, roughness: 0.3 });
  const lampRed = new THREE.MeshStandardMaterial({ color: 0x4a1515, emissive: 0xff2b2b, emissiveIntensity: 0, roughness: 0.3 });
  mesh(cylY(0.045, 0.08, 24), lampRed, beacon, 0, 1.34, 0);
  mesh(cylY(0.045, 0.08, 24), lampAmber, beacon, 0, 1.425, 0);
  mesh(cylY(0.045, 0.08, 24), lampGreen, beacon, 0, 1.51, 0);
  mesh(cylY(0.03, 0.03, 24), M.dark, beacon, 0, 1.565, 0);

  /* ─── Convoyeur (le long de Z, à gauche du robot) ─── */
  const CX = -1.02, BELT_Y = 0.55, Z0 = -2.6, ZSTOP = 0.2, BOX = 0.13;
  const conveyor = new THREE.Group(); scene.add(conveyor);
  const beltLen = ZSTOP + 0.2 - Z0;
  const beltMid = (ZSTOP + 0.2 + Z0) / 2;
  const beltTexCanvas = document.createElement('canvas'); beltTexCanvas.width = 64; beltTexCanvas.height = 64;
  const bctx = beltTexCanvas.getContext('2d');
  bctx.fillStyle = '#1b1e23'; bctx.fillRect(0, 0, 64, 64);
  bctx.fillStyle = '#25292f'; for (let y = 0; y < 64; y += 8) bctx.fillRect(0, y, 64, 3);
  const beltTex = new THREE.CanvasTexture(beltTexCanvas);
  beltTex.wrapS = beltTex.wrapT = THREE.RepeatWrapping; beltTex.repeat.set(1, beltLen * 6);
  beltTex.colorSpace = THREE.SRGBColorSpace;
  const beltMat = new THREE.MeshStandardMaterial({ map: beltTex, roughness: 0.9, metalness: 0 });
  const belt = mesh(new THREE.BoxGeometry(0.34, 0.02, beltLen), beltMat, conveyor, CX, BELT_Y - 0.01, beltMid);
  belt.castShadow = false;
  mesh(new THREE.BoxGeometry(0.035, 0.08, beltLen + 0.04), M.alu, conveyor, CX - 0.19, BELT_Y - 0.02, beltMid);
  mesh(new THREE.BoxGeometry(0.035, 0.08, beltLen + 0.04), M.alu, conveyor, CX + 0.19, BELT_Y - 0.02, beltMid);
  mesh(cylX(0.045, 0.36), M.steel, conveyor, CX, BELT_Y - 0.045, ZSTOP + 0.2);
  for (let z = Z0 + 0.3; z < ZSTOP + 0.2; z += 0.75) {
    mesh(new THREE.BoxGeometry(0.04, BELT_Y - 0.06, 0.04), M.alu, conveyor, CX - 0.17, (BELT_Y - 0.06) / 2, z);
    mesh(new THREE.BoxGeometry(0.04, BELT_Y - 0.06, 0.04), M.alu, conveyor, CX + 0.17, (BELT_Y - 0.06) / 2, z);
    mesh(new THREE.BoxGeometry(0.34, 0.03, 0.03), M.alu, conveyor, CX, 0.16, z);
  }
  mesh(new THREE.BoxGeometry(0.3, 0.06, 0.025), M.tape, conveyor, CX, BELT_Y + 0.03, ZSTOP + BOX / 2 + 0.02);   // butée
  const sensorMat = new THREE.MeshStandardMaterial({ color: 0x222222, emissive: 0x2bff8a, emissiveIntensity: 0.2 });
  mesh(new THREE.BoxGeometry(0.03, 0.05, 0.05), M.dark, conveyor, CX + 0.2, BELT_Y + 0.05, ZSTOP);
  mesh(new THREE.SphereGeometry(0.012, 12, 8), sensorMat, conveyor, CX + 0.2, BELT_Y + 0.085, ZSTOP);

  /* ─── Palette ─── */
  const PX = 0.62, PZ = 0.98, PALLET_TOP = 0.14;
  const pallet = new THREE.Group(); pallet.position.set(PX, 0, PZ); scene.add(pallet);
  for (let i = -1; i <= 1; i += 1) {
    mesh(new THREE.BoxGeometry(0.62, 0.02, 0.1), M.wood, pallet, 0, 0.13, i * 0.25);
    mesh(new THREE.BoxGeometry(0.1, 0.09, 0.62), M.wood, pallet, i * 0.26, 0.075, 0);
    mesh(new THREE.BoxGeometry(0.62, 0.02, 0.1), M.wood, pallet, 0, 0.02, i * 0.25);
  }
  for (let i = -2; i <= 2; i += 1) mesh(new THREE.BoxGeometry(0.62, 0.02, 0.09), M.wood, pallet, 0, 0.13, i * 0.13);

  const SLOTS = [];
  for (let layer = 0; layer < 2; layer += 1) {
    for (let k = 0; k < 4; k += 1) {
      const sx = (k % 2 ? 1 : -1) * 0.085, sz = (k < 2 ? -1 : 1) * 0.085;
      SLOTS.push(new THREE.Vector3(PX + sx, PALLET_TOP + 0.005 + BOX / 2 + layer * BOX, PZ + sz));
    }
  }

  /* Cartons */
  const boxGeo = rbox(BOX, BOX, BOX, 0.008);
  const tapeGeo = new THREE.BoxGeometry(0.03, 0.003, BOX + 0.002);
  const labelGeo = new THREE.PlaneGeometry(0.06, 0.035);
  function makeBox() {
    const b = mesh(boxGeo, M.card, null);
    mesh(tapeGeo, M.boxTape, b, 0, BOX / 2, 0);
    const l = mesh(labelGeo, M.label, b, BOX / 2 + 0.001, 0.01, 0); l.rotation.y = Math.PI / 2; l.castShadow = false;
    const l2 = mesh(labelGeo, M.label, b, -BOX / 2 - 0.001, 0.01, 0); l2.rotation.y = -Math.PI / 2; l2.castShadow = false;
    scene.add(b);
    return b;
  }
  const queue = [];          // cartons sur le convoyeur
  const placed = [];         // cartons sur la palette
  let held = null;

  /* ─── Cinématique inverse (bras anthropomorphe, outil vertical vers le bas) ─── */
  function ik(p, toolYaw) {
    const yaw = Math.atan2(-p.z, p.x);
    const r = Math.hypot(p.x, p.z);
    const wx = r - A1, wy = p.y + D6 - H0;
    const d = Math.min(Math.hypot(wx, wy), L2 + L3 - 1e-4);
    const phi = Math.atan2(wy, wx);
    const c = Math.max(-1, Math.min(1, (L2 * L2 + d * d - L3 * L3) / (2 * L2 * d)));
    const alpha = phi + Math.acos(c);
    const ex = L2 * Math.cos(alpha), ey = L2 * Math.sin(alpha);
    const beta = Math.atan2(wy - ey, wx - ex);
    const s = alpha - Math.PI / 2;
    const e = beta - s;
    const w = -Math.PI / 2 - beta;
    return [yaw, s, e, 0, w, yaw - (toolYaw || 0)];
  }
  function apply(q) {
    j1.rotation.y = q[0]; j2.rotation.z = q[1]; j3.rotation.z = q[2];
    j4.rotation.x = q[3]; j5.rotation.z = q[4]; j6.rotation.x = q[5];
  }
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  function lerpQ(a, b, t) { return a.map(function (v, i) { return v + (b[i] - v) * t; }); }

  /* Ajuste les hauteurs de base : la pose de repos (sans carton) */
  const PICK = new THREE.Vector3(CX, BELT_Y + BOX / 2, ZSTOP);
  const up = (v, h) => new THREE.Vector3(v.x, v.y + h, v.z);
  const HOME = ik(new THREE.Vector3(-0.35, 1.05, 0.75), 0);
  HOME[3] = 0.0;

  let q = HOME.slice();
  let gripOpen = 1;          // 1 ouvert, 0 fermé
  apply(q);

  /* Programme : liste de segments (déplacement articulaire, attente, action) */
  let program = [];
  let seg = null, segT = 0, slotIndex = 0, parts = 0;
  const FINGER_OPEN = 0.1, FINGER_CLOSED = BOX / 2 + 0.011;

  function move(to, dur) { program.push({ kind: 'move', to: to, dur: dur }); }
  function wait(dur, fn) { program.push({ kind: 'wait', dur: dur, fn: fn }); }
  function gripper(open, dur) { program.push({ kind: 'grip', open: open, dur: dur || 0.35 }); }
  function call(fn) { program.push({ kind: 'call', dur: 0, fn: fn }); }

  function planCycle() {
    const slot = SLOTS[slotIndex];
    const yawPick = 0, yawPlace = 0;
    move(ik(up(PICK, 0.28), yawPick), 1.1);
    call(function () { program.unshift({ kind: 'waitPart', dur: 0 }); });
    move(ik(up(PICK, 0.0), yawPick), 0.55);
    gripper(false, 0.3);
    call(attachPart);
    move(ik(up(PICK, 0.3), yawPick), 0.5);
    move(ik(up(slot, 0.32), yawPlace), 1.35);
    move(ik(up(slot, 0.0), yawPlace), 0.6);
    gripper(true, 0.3);
    call(releasePart);
    move(ik(up(slot, 0.3), yawPlace), 0.5);
    call(function () {
      slotIndex += 1;
      if (slotIndex >= SLOTS.length) {
        program.unshift({ kind: 'clearPallet', dur: 1.2 });
        slotIndex = 0;
      }
    });
  }

  function attachPart() {
    const part = queue.length && queue[0].stopped ? queue.shift() : null;
    if (!part) return;
    held = part.mesh;
    grip.attach(held);
    held.position.set(0, 0, 0);
  }
  function releasePart() {
    if (!held) return;
    scene.attach(held);
    const slot = SLOTS[slotIndex];
    held.position.copy(slot);
    held.rotation.set(0, 0, 0);
    placed.push(held);
    held = null;
    parts += 1;
  }

  /* Convoyeur : arrivée des cartons */
  const SPEED = 0.32;
  let spawnTimer = 0;
  let beltOffset = 0;
  function spawn() {
    const m = makeBox();
    m.position.set(CX, BELT_Y + BOX / 2, Z0 + 0.1);
    m.rotation.y = (Math.random() - 0.5) * 0.06;
    queue.push({ mesh: m, stopped: false });
  }
  function updateConveyor(dt) {
    beltOffset -= dt * SPEED * 6;
    beltTex.offset.y = beltOffset;
    spawnTimer -= dt;
    const last = queue[queue.length - 1];
    if (spawnTimer <= 0 && queue.length < 4 && (!last || last.mesh.position.z > Z0 + 0.1 + BOX + 0.15)) {
      spawn(); spawnTimer = 2.2;
    }
    for (let i = 0; i < queue.length; i += 1) {
      const it = queue[i];
      const limit = i === 0 ? ZSTOP : queue[i - 1].mesh.position.z - BOX - 0.02;
      const z = it.mesh.position.z;
      it.mesh.position.z = Math.min(limit, z + SPEED * dt);
      it.stopped = it.mesh.position.z >= limit - 1e-4;
    }
    const ready = queue.length && queue[0].stopped;
    sensorMat.emissiveIntensity = ready ? 2.2 : 0.2;
  }

  /* Pré-remplissage pour que la scène soit vivante dès l'affichage */
  for (let i = 0; i < 3; i += 1) {
    const m = makeBox();
    m.position.set(CX, BELT_Y + BOX / 2, ZSTOP - i * (BOX + 0.25));
    queue.push({ mesh: m, stopped: i === 0 });
  }
  for (let i = 0; i < 3; i += 1) {
    const m = makeBox(); m.position.copy(SLOTS[i]); placed.push(m);
  }
  slotIndex = 3;
  parts = 3;

  function step(dt) {
    updateConveyor(dt);
    if (!seg) {
      if (!program.length) planCycle();
      seg = program.shift();
      seg.from = q.slice();
      seg.gripFrom = gripOpen;
      segT = 0;
    }
    segT += dt;
    const t = seg.dur ? Math.min(1, segT / seg.dur) : 1;
    let done = t >= 1;
    if (seg.kind === 'move') {
      q = lerpQ(seg.from, seg.to, ease(t));
    } else if (seg.kind === 'grip') {
      gripOpen = seg.gripFrom + ((seg.open ? 1 : 0) - seg.gripFrom) * ease(t);
    } else if (seg.kind === 'waitPart') {
      done = queue.length > 0 && queue[0].stopped;
    } else if (seg.kind === 'clearPallet') {
      const k = 1 - ease(t);
      placed.forEach(function (b) { b.scale.setScalar(Math.max(0.001, k)); });
      if (done) { placed.forEach(function (b) { scene.remove(b); }); placed.length = 0; }
    } else if (seg.kind === 'call' || seg.kind === 'wait') {
      if (done && seg.fn) seg.fn();
    }
    if (done) seg = null;
    apply(q);
    const f = FINGER_CLOSED + (FINGER_OPEN - FINGER_CLOSED) * gripOpen;
    fingerA.position.z = f; fingerB.position.z = -f;
  }

  /* Caméra, dimensionnement */
  let width = 0, height = 0;
  function resize() {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h || (w === width && h === height)) return;
    width = w; height = h;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = 30;
    camera.updateProjectionMatrix();
  }
  function placeCamera(time) {
    const a = 0.72 + Math.sin(time * 0.12) * 0.12;
    const dist = 5.1 * Math.pow(Math.max(1, 1.9 / camera.aspect), 0.8);
    camera.position.set(target.x + Math.sin(a) * dist, 2.45 + Math.sin(time * 0.09) * 0.08, target.z + Math.cos(a) * dist);
    camera.lookAt(target);
  }

  /* Affichage tête haute */
  const hud = host.querySelector('[data-robot-hud]');
  const joints = hud ? Array.from(hud.querySelectorAll('[data-joint]')) : [];
  const counter = hud ? hud.querySelector('[data-parts]') : null;
  const deg = (r) => {
    let d = r * 180 / Math.PI;
    d = ((d + 540) % 360) - 180;
    return (d >= 0 ? '+' : '−') + Math.abs(d).toFixed(1).padStart(5, '0') + '°';
  };
  let hudTimer = 0;
  function updateHud(dt) {
    hudTimer -= dt;
    if (hudTimer > 0) return;
    hudTimer = 0.1;
    joints.forEach(function (el, i) { el.textContent = deg(q[i]); });
    if (counter) counter.textContent = String(parts).padStart(3, '0');
  }

  let running = false, visible = false, last = 0, clockT = 0, raf = 0;
  function frame(now) {
    raf = 0;
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
    last = now;
    clockT += dt;
    resize();
    step(dt);
    placeCamera(clockT);
    updateHud(dt);
    lampGreen.emissiveIntensity = 1.4 + Math.sin(clockT * 3) * 0.25;
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }
  function start() {
    if (running || reduced || !visible || document.hidden) return;
    running = true; last = performance.now();
    raf = requestAnimationFrame(frame);
  }
  function stop() { running = false; if (raf) cancelAnimationFrame(raf); raf = 0; }

  function renderStill() {
    resize(); placeCamera(0); updateHud(1); renderer.render(scene, camera);
  }

  if ('ResizeObserver' in window) new ResizeObserver(function () { resize(); if (!running) renderStill(); }).observe(host);
  new IntersectionObserver(function (entries) {
    visible = entries[0].isIntersecting;
    if (visible) start(); else stop();
  }, { threshold: 0.05 }).observe(host);
  document.addEventListener('visibilitychange', function () { if (document.hidden) stop(); else start(); });

  if (reduced) {
    q = ik(up(PICK, 0.12), 0); apply(q);
  }
  renderStill();
  host.classList.add('is-3d');
  return true;
}
