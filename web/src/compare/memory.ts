import { Mesh, type BufferGeometry, type Object3D } from 'three';

function geometryBytes(geometry: BufferGeometry): number {
  let bytes = geometry.index?.array.byteLength ?? 0;
  for (const attribute of Object.values(geometry.attributes)) {
    bytes += attribute.array.byteLength;
  }
  return bytes;
}

export function comparisonGeometryBytes(root: Object3D): number {
  const geometries = new Map<string, BufferGeometry>();
  root.traverse((object) => {
    if (object instanceof Mesh)
      geometries.set(object.geometry.uuid, object.geometry);
  });
  return [...geometries.values()].reduce(
    (total, geometry) => total + geometryBytes(geometry),
    0,
  );
}
