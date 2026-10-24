import * as THREE from 'three';

export const MOCK_NOTE =
  'Illustrative mock-up only: block sizes and positions are not taken from proposal documents.';

// Open lot west of the existing Markley building, clear of context buildings,
// roads, rail and water. Scene x is east; scene z is south.
const LOT_CENTER_X = -135;
const LOT_CENTER_Z = 20;

export const MOCK_FOCUS = {
  target: [LOT_CENTER_X, 10, LOT_CENTER_Z] as const,
  position: [LOT_CENTER_X + 120, 75, LOT_CENTER_Z + 130] as const,
};

function withEdges(mesh: THREE.Mesh, color: number): THREE.Mesh {
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry),
    new THREE.LineBasicMaterial({ color }),
  );
  mesh.add(edges);
  return mesh;
}

// Demo-only massing beside the site, enabled with ?mock=1.
export function buildMockProposal(): THREE.Group {
  const group = new THREE.Group();
  group.name = 'Illustrative mock proposal';
  group.position.set(LOT_CENTER_X, 0, LOT_CENTER_Z);

  const hall = withEdges(
    new THREE.Mesh(
      new THREE.BoxGeometry(70, 24, 34),
      new THREE.MeshStandardMaterial({
        color: 0xf07a3f,
        emissive: 0x7a2a08,
        emissiveIntensity: 0.35,
        roughness: 0.55,
      }),
    ),
    0xffe2cc,
  );
  hall.position.set(0, 12, -8);
  group.add(hall);

  const pad = new THREE.Mesh(
    new THREE.PlaneGeometry(74, 54),
    new THREE.MeshBasicMaterial({
      color: 0xf07a3f,
      transparent: true,
      opacity: 0.18,
    }),
  );
  pad.rotation.x = -Math.PI / 2;
  pad.position.y = 0.15;
  group.add(pad);

  const generatorMaterial = new THREE.MeshStandardMaterial({
    color: 0x2f6fa3,
    emissive: 0x0b2a45,
    emissiveIntensity: 0.4,
  });
  for (let i = 0; i < 6; i += 1) {
    const generator = withEdges(
      new THREE.Mesh(new THREE.BoxGeometry(9, 4, 5), generatorMaterial),
      0xcfe6ff,
    );
    generator.position.set(-27.5 + i * 11, 2, 17);
    group.add(generator);
  }
  return group;
}

export function mockEnabled(): boolean {
  return new URLSearchParams(window.location.search).get('mock') === '1';
}
