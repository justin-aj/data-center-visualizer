import {
  Box3,
  EdgesGeometry,
  Group,
  LineSegments,
  Mesh,
  MeshStandardMaterial,
  Vector3,
  type Material,
  type Object3D,
} from 'three';

import type {
  ConfidenceStatus,
  FeatureState,
  Proposal,
  ProposalFeature,
} from '../data/types';
import { extrudedPolygonMesh, wideLineMeshes } from './builders';
import {
  createHatchTexture,
  createStatusSprite,
  type DetailLevel,
  outlineMaterial,
} from './textures';
import { sceneStyle } from './style';

export interface BuiltProposal {
  group: Group;
  featureCount: number;
  unknownHeightCount: number;
  estimatedHeightCount: number;
}

function stateColor(state: FeatureState): string {
  if (state === 'existing') return sceneStyle.contextBuilding;
  if (state === 'removed') return sceneStyle.shadow;
  return sceneStyle.proposal;
}

function featureMaterial(
  feature: ProposalFeature,
  detailLevel: DetailLevel,
): MeshStandardMaterial {
  const estimated = feature.height.status === 'estimated';
  const removed = feature.state === 'removed';
  const hatch =
    estimated && detailLevel === 'full' ? createHatchTexture() : null;
  return new MeshStandardMaterial({
    color: stateColor(feature.state),
    map: hatch,
    roughness: 0.78,
    metalness: 0,
    opacity: removed ? 0.52 : 1,
    transparent: removed,
  });
}

function addOutline(mesh: Mesh, estimated: boolean): void {
  const outline = new LineSegments(
    new EdgesGeometry(mesh.geometry, 24),
    outlineMaterial(estimated),
  );
  if (estimated) outline.computeLineDistances();
  outline.userData['confidenceTreatment'] = estimated ? 'dashed' : 'solid';
  mesh.add(outline);
}

function outlineMeshes(root: Object3D, estimated: boolean): void {
  const meshes: Mesh[] = [];
  root.traverse((object) => {
    if (object instanceof Mesh) meshes.push(object);
  });
  for (const mesh of meshes) addOutline(mesh, estimated);
}

function featureGeometry(feature: ProposalFeature, material: Material): Group {
  const group = new Group();
  const height = feature.height.valueM;
  const symbolicHeight = 0.08;
  const renderedHeight = height ?? symbolicHeight;

  if (feature.geometry.type === 'Polygon') {
    group.add(
      extrudedPolygonMesh(
        feature.geometry,
        renderedHeight,
        feature.baseElevationM,
        material,
      ),
    );
  } else {
    if (feature.widthM === null) {
      throw new Error(`Line feature ${feature.id} has no width.`);
    }
    group.add(
      wideLineMeshes(
        feature.geometry,
        feature.widthM,
        renderedHeight,
        feature.baseElevationM,
        material,
      ),
    );
  }

  const unknown = height === null;
  group.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    object.castShadow = !unknown;
    object.userData['shadowConfidence'] = unknown
      ? 'none'
      : feature.height.status;
  });
  outlineMeshes(group, feature.height.status === 'estimated');
  return group;
}

function statusLabel(feature: ProposalFeature): string {
  const state = feature.state.replace('_', ' ');
  const confidence = feature.height.status;
  const unknownMarker = confidence === 'unknown' ? ' ?' : '';
  return `${state} · ${confidence}${unknownMarker}`;
}

function attachFeatureData(root: Object3D, feature: ProposalFeature): void {
  root.traverse((object) => {
    object.userData['featureId'] = feature.id;
    object.userData['category'] = feature.category;
    object.userData['state'] = feature.state;
    object.userData['heightStatus'] = feature.height.status;
    object.userData['label'] = feature.label;
  });
}

function buildFeature(
  feature: ProposalFeature,
  detailLevel: DetailLevel,
): Group {
  const group = featureGeometry(feature, featureMaterial(feature, detailLevel));
  group.name = feature.label;
  attachFeatureData(group, feature);

  const bounds = new Box3().setFromObject(group);
  const center = bounds.getCenter(new Vector3());
  const badge = createStatusSprite(statusLabel(feature));
  badge.position.set(center.x, bounds.max.y + 4.5, center.z);
  badge.userData['featureId'] = feature.id;
  group.add(badge);
  return group;
}

export function buildProposalFeatures(
  proposal: Proposal,
  detailLevel: DetailLevel,
): BuiltProposal {
  const group = new Group();
  group.name = `Proposal features: ${detailLevel} detail`;

  for (const feature of proposal.features) {
    group.add(buildFeature(feature, detailLevel));
  }

  return {
    group,
    featureCount: proposal.features.length,
    unknownHeightCount: proposal.features.filter(
      (feature) => feature.height.status === 'unknown',
    ).length,
    estimatedHeightCount: proposal.features.filter(
      (feature) => feature.height.status === 'estimated',
    ).length,
  };
}

export function confidenceTreatment(
  status: ConfidenceStatus,
  detailLevel: DetailLevel,
): 'solid' | 'hatched-dashed' | 'dashed' | 'flat-question' {
  if (status === 'unknown') return 'flat-question';
  if (status === 'estimated') {
    return detailLevel === 'full' ? 'hatched-dashed' : 'dashed';
  }
  return 'solid';
}
